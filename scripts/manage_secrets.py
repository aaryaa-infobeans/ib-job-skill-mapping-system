#!/usr/bin/env python3
"""
Secrets Management Script

This script helps manage secrets in AWS Secrets Manager:
1. Initialize secrets with placeholder values
2. Update secrets with actual values
3. Rotate secrets
4. Retrieve secrets for application deployment
5. Audit secret access
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 is required. Install with: pip install boto3")
    sys.exit(1)


class SecretsManager:
    """Manages AWS Secrets Manager operations."""
    
    def __init__(self, region: str, name_prefix: str):
        self.region = region
        self.name_prefix = name_prefix
        self.client = boto3.client('secretsmanager', region_name=region)
    
    def list_secrets(self) -> None:
        """List all secrets for this application."""
        print(f"\n🔐 Secrets for {self.name_prefix}:\n")
        
        try:
            response = self.client.list_secrets(
                Filters=[
                    {'Key': 'name', 'Values': [f'{self.name_prefix}-*']}
                ]
            )
            
            if not response['SecretList']:
                print("  No secrets found.\n")
                return
            
            for secret in response['SecretList']:
                name = secret['Name']
                created = secret.get('CreatedDate', 'Unknown')
                last_changed = secret.get('LastChangedDate', 'Unknown')
                rotation = secret.get('RotationEnabled', False)
                
                print(f"  • {name}")
                print(f"    ARN: {secret['ARN']}")
                print(f"    Created: {created}")
                print(f"    Last Changed: {last_changed}")
                print(f"    Rotation: {'Enabled' if rotation else 'Disabled'}")
                
                # Get tags
                tags = secret.get('Tags', [])
                if tags:
                    tag_dict = {t['Key']: t['Value'] for t in tags}
                    print(f"    Tags: {tag_dict}")
                print()
        
        except ClientError as e:
            print(f"❌ Error listing secrets: {e}")
            sys.exit(1)
    
    def get_secret(self, secret_type: str) -> Dict[str, Any]:
        """Retrieve a secret value."""
        secret_name = f"{self.name_prefix}-{secret_type}"
        
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            return secret_data
        
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"❌ Secret not found: {secret_name}")
            else:
                print(f"❌ Error retrieving secret: {e}")
            sys.exit(1)
    
    def update_secret(self, secret_type: str, secret_data: Dict[str, Any]) -> None:
        """Update a secret value."""
        secret_name = f"{self.name_prefix}-{secret_type}"
        
        try:
            self.client.put_secret_value(
                SecretId=secret_name,
                SecretString=json.dumps(secret_data)
            )
            print(f"✅ Secret updated: {secret_name}")
        
        except ClientError as e:
            print(f"❌ Error updating secret: {e}")
            sys.exit(1)
    
    def create_secret(self, secret_type: str, secret_data: Dict[str, Any],
                     description: str = "") -> None:
        """Create a new secret."""
        secret_name = f"{self.name_prefix}-{secret_type}"
        
        try:
            self.client.create_secret(
                Name=secret_name,
                Description=description,
                SecretString=json.dumps(secret_data),
                Tags=[
                    {'Key': 'Project', 'Value': self.name_prefix},
                    {'Key': 'ManagedBy', 'Value': 'secrets-manager-script'}
                ]
            )
            print(f"✅ Secret created: {secret_name}")
        
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceExistsException':
                print(f"⚠️  Secret already exists: {secret_name}")
                response = input("Update existing secret? (y/N): ")
                if response.lower() == 'y':
                    self.update_secret(secret_type, secret_data)
            else:
                print(f"❌ Error creating secret: {e}")
                sys.exit(1)
    
    def rotate_secret(self, secret_type: str, rotation_lambda_arn: str) -> None:
        """Enable automatic rotation for a secret."""
        secret_name = f"{self.name_prefix}-{secret_type}"
        
        try:
            self.client.rotate_secret(
                SecretId=secret_name,
                RotationLambdaARN=rotation_lambda_arn,
                RotationRules={
                    'AutomaticallyAfterDays': 90
                }
            )
            print(f"✅ Rotation enabled for: {secret_name}")
        
        except ClientError as e:
            print(f"❌ Error enabling rotation: {e}")
            sys.exit(1)
    
    def export_secrets_template(self, output_file: Path) -> None:
        """Export secrets to a template file for configuration."""
        template = {
            "oauth_client": {
                "client_id": "<YOUR_OAUTH_CLIENT_ID>",
                "client_secret": "<YOUR_OAUTH_CLIENT_SECRET>",
                "tenant_id": "<YOUR_TENANT_ID>"
            },
            "llm_api_keys": {
                "openai_api_key": "<YOUR_OPENAI_API_KEY>",
                "azure_openai_endpoint": "<YOUR_AZURE_ENDPOINT>",
                "azure_openai_api_key": "<YOUR_AZURE_API_KEY>",
                "azure_openai_deployment": "<YOUR_DEPLOYMENT_NAME>",
                "anthropic_api_key": "<YOUR_ANTHROPIC_API_KEY>"
            }
        }
        
        output_file.write_text(json.dumps(template, indent=2))
        print(f"✅ Template exported to: {output_file}")
        print(f"   Edit this file and use 'update-from-file' to set secrets.")
    
    def update_from_file(self, secrets_file: Path) -> None:
        """Update secrets from a JSON file."""
        if not secrets_file.exists():
            print(f"❌ File not found: {secrets_file}")
            sys.exit(1)
        
        try:
            secrets_data = json.loads(secrets_file.read_text())
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in file: {e}")
            sys.exit(1)
        
        for secret_type, secret_value in secrets_data.items():
            # Validate secret has actual values (not placeholders)
            if any('<YOUR_' in str(v) for v in secret_value.values()):
                print(f"⚠️  Skipping {secret_type}: contains placeholder values")
                continue
            
            print(f"Updating {secret_type}...")
            self.update_secret(secret_type, secret_value)
    
    def generate_app_config(self, output_file: Path) -> None:
        """Generate application configuration from secrets."""
        print("\n📝 Generating application configuration...\n")
        
        # Retrieve all secrets
        try:
            db_password = self.get_secret("db-master-password")
            oauth = self.get_secret("oauth-client")
            llm_keys = self.get_secret("llm-api-keys")
            app_secrets = self.get_secret("application-secrets")
            redis_creds = self.get_secret("redis-credentials")
        except Exception as e:
            print(f"❌ Error retrieving secrets: {e}")
            return
        
        # Build configuration
        config = {
            "database": {
                "password_secret_arn": f"arn:aws:secretsmanager:{self.region}:*:secret:{self.name_prefix}-db-master-password-*"
            },
            "oauth": {
                "client_id": oauth.get("client_id"),
                "tenant_id": oauth.get("tenant_id"),
                "secret_arn": f"arn:aws:secretsmanager:{self.region}:*:secret:{self.name_prefix}-oauth-client-*"
            },
            "llm": {
                "provider": "azure_openai" if llm_keys.get("azure_openai_api_key") else "openai",
                "secret_arn": f"arn:aws:secretsmanager:{self.region}:*:secret:{self.name_prefix}-llm-api-keys-*"
            },
            "redis": {
                "host": redis_creds.get("host"),
                "port": redis_creds.get("port"),
                "secret_arn": f"arn:aws:secretsmanager:{self.region}:*:secret:{self.name_prefix}-redis-credentials-*"
            },
            "application": {
                "secret_arn": f"arn:aws:secretsmanager:{self.region}:*:secret:{self.name_prefix}-application-secrets-*"
            }
        }
        
        output_file.write_text(json.dumps(config, indent=2))
        print(f"✅ Configuration exported to: {output_file}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage AWS Secrets Manager secrets for the application"
    )
    
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)"
    )
    
    parser.add_argument(
        "--prefix",
        default="ib-job-skill-mapping-prod",
        help="Name prefix for secrets (default: ib-job-skill-mapping-prod)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List secrets
    subparsers.add_parser("list", help="List all secrets")
    
    # Get secret
    get_parser = subparsers.add_parser("get", help="Get a secret value")
    get_parser.add_argument("secret_type", help="Secret type (e.g., oauth-client)")
    
    # Export template
    export_parser = subparsers.add_parser("export-template", help="Export secrets template")
    export_parser.add_argument(
        "--output",
        default="secrets-template.json",
        help="Output file (default: secrets-template.json)"
    )
    
    # Update from file
    update_parser = subparsers.add_parser("update-from-file", help="Update secrets from JSON file")
    update_parser.add_argument("file", help="JSON file with secret values")
    
    # Generate app config
    config_parser = subparsers.add_parser("generate-config", help="Generate application config")
    config_parser.add_argument(
        "--output",
        default="app-config.json",
        help="Output file (default: app-config.json)"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    manager = SecretsManager(args.region, args.prefix)
    
    if args.command == "list":
        manager.list_secrets()
    
    elif args.command == "get":
        secret_data = manager.get_secret(args.secret_type)
        print(json.dumps(secret_data, indent=2))
    
    elif args.command == "export-template":
        manager.export_secrets_template(Path(args.output))
    
    elif args.command == "update-from-file":
        manager.update_from_file(Path(args.file))
    
    elif args.command == "generate-config":
        manager.generate_app_config(Path(args.output))


if __name__ == "__main__":
    main()
