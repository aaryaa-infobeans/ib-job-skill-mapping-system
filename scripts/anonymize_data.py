#!/usr/bin/env python3
"""
Data Anonymization Script for Staging Environment
TASK-PII-202: Load production-like data into staging (anonymized)

This script anonymizes production data for use in staging environment testing.
"""

import argparse
import hashlib
import json
import logging
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import faker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataAnonymizer:
    """Anonymizes production data for staging environment."""
    
    def __init__(self, seed: int = 42):
        self.faker = faker.Faker()
        self.faker.seed_instance(seed)
        random.seed(seed)
        self.anonymization_map: Dict[str, str] = {}
        
    def anonymize_name(self, name: str) -> str:
        """Anonymize a person's name consistently."""
        if name in self.anonymization_map:
            return self.anonymization_map[name]
        
        # Generate fake name
        fake_name = self.faker.name()
        self.anonymization_map[name] = fake_name
        return fake_name
    
    def anonymize_email(self, email: str) -> str:
        """Anonymize email address consistently."""
        if email in self.anonymization_map:
            return self.anonymization_map[email]
        
        # Generate fake email
        fake_email = self.faker.email()
        self.anonymization_map[email] = fake_email
        return fake_email
    
    def anonymize_phone(self, phone: str) -> str:
        """Anonymize phone number consistently."""
        if phone in self.anonymization_map:
            return self.anonymization_map[phone]
        
        # Generate fake phone
        fake_phone = self.faker.phone_number()
        self.anonymization_map[phone] = fake_phone
        return fake_phone
    
    def anonymize_organization(self, org: str) -> str:
        """Anonymize organization name consistently."""
        if org in self.anonymization_map:
            return self.anonymization_map[org]
        
        # Generate fake company
        fake_org = self.faker.company()
        self.anonymization_map[org] = fake_org
        return fake_org
    
    def anonymize_profile_text(self, text: str) -> str:
        """
        Anonymize profile text by replacing detected PII.
        Uses regex patterns to detect and replace PII.
        """
        if not text:
            return text
        
        anonymized = text
        
        # Anonymize email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, anonymized)
        for email in emails:
            anonymized = anonymized.replace(email, self.anonymize_email(email))
        
        # Anonymize phone numbers
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        phones = re.findall(phone_pattern, anonymized)
        for phone in phones:
            anonymized = anonymized.replace(phone, self.anonymize_phone(phone))
        
        # Anonymize SSN
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        ssns = re.findall(ssn_pattern, anonymized)
        for ssn in ssns:
            fake_ssn = f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
            anonymized = anonymized.replace(ssn, fake_ssn)
        
        return anonymized
    
    def anonymize_record(self, record: Dict) -> Dict:
        """
        Anonymize a single database record.
        
        Args:
            record: Dictionary containing profile data
            
        Returns:
            Anonymized record
        """
        anonymized = record.copy()
        
        # Anonymize name fields
        if 'name' in anonymized:
            anonymized['name'] = self.anonymize_name(anonymized['name'])
        
        if 'first_name' in anonymized:
            anonymized['first_name'] = self.faker.first_name()
        
        if 'last_name' in anonymized:
            anonymized['last_name'] = self.faker.last_name()
        
        # Anonymize contact info
        if 'email' in anonymized:
            anonymized['email'] = self.anonymize_email(anonymized['email'])
        
        if 'phone' in anonymized:
            anonymized['phone'] = self.anonymize_phone(anonymized['phone'])
        
        # Anonymize profile text
        if 'profile_text' in anonymized:
            anonymized['profile_text'] = self.anonymize_profile_text(anonymized['profile_text'])
        
        if 'resume_text' in anonymized:
            anonymized['resume_text'] = self.anonymize_profile_text(anonymized['resume_text'])
        
        # Anonymize organization
        if 'company' in anonymized:
            anonymized['company'] = self.anonymize_organization(anonymized['company'])
        
        # Generate checksum for validation
        anonymized['anonymization_checksum'] = self._generate_checksum(anonymized)
        
        return anonymized
    
    def _generate_checksum(self, record: Dict) -> str:
        """Generate SHA-256 checksum for record validation."""
        # Create deterministic string representation
        text = json.dumps(record, sort_keys=True)
        return hashlib.sha256(text.encode()).hexdigest()
    
    def anonymize_dataset(
        self,
        input_file: Path,
        output_file: Path,
        target_count: int = 250000
    ) -> Dict:
        """
        Anonymize entire dataset.
        
        Args:
            input_file: Path to input data (JSON lines)
            output_file: Path to output anonymized data
            target_count: Target number of records (TASK-PII-202: 250,000)
            
        Returns:
            Statistics about anonymization
        """
        logger.info(f"Anonymizing dataset: {input_file}")
        logger.info(f"Target count: {target_count} records")
        
        stats = {
            "input_records": 0,
            "output_records": 0,
            "anonymized_fields": {
                "names": 0,
                "emails": 0,
                "phones": 0,
                "organizations": 0
            },
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None
        }
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line_num, line in enumerate(infile, 1):
                if line_num > target_count:
                    logger.info(f"Reached target count: {target_count}")
                    break
                
                try:
                    record = json.loads(line.strip())
                    stats["input_records"] += 1
                    
                    # Anonymize record
                    anonymized = self.anonymize_record(record)
                    
                    # Write anonymized record
                    outfile.write(json.dumps(anonymized) + '\n')
                    stats["output_records"] += 1
                    
                    # Update stats
                    if 'name' in record and record['name'] != anonymized.get('name'):
                        stats["anonymized_fields"]["names"] += 1
                    if 'email' in record and record['email'] != anonymized.get('email'):
                        stats["anonymized_fields"]["emails"] += 1
                    if 'phone' in record and record['phone'] != anonymized.get('phone'):
                        stats["anonymized_fields"]["phones"] += 1
                    if 'company' in record and record['company'] != anonymized.get('company'):
                        stats["anonymized_fields"]["organizations"] += 1
                    
                    # Log progress
                    if line_num % 10000 == 0:
                        logger.info(f"Processed {line_num:,} records...")
                
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse line {line_num}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Failed to anonymize record {line_num}: {e}")
                    continue
        
        stats["end_time"] = datetime.utcnow().isoformat()
        
        logger.info(f"Anonymization complete:")
        logger.info(f"  Input records: {stats['input_records']:,}")
        logger.info(f"  Output records: {stats['output_records']:,}")
        logger.info(f"  Names anonymized: {stats['anonymized_fields']['names']:,}")
        logger.info(f"  Emails anonymized: {stats['anonymized_fields']['emails']:,}")
        logger.info(f"  Phones anonymized: {stats['anonymized_fields']['phones']:,}")
        logger.info(f"  Organizations anonymized: {stats['anonymized_fields']['organizations']:,}")
        
        return stats
    
    def generate_synthetic_data(
        self,
        output_file: Path,
        count: int = 250000
    ) -> Dict:
        """
        Generate synthetic profile data for testing.
        
        Args:
            output_file: Path to output file
            count: Number of records to generate (TASK-PII-202: 250,000)
            
        Returns:
            Statistics about generation
        """
        logger.info(f"Generating {count:,} synthetic records...")
        
        stats = {
            "generated_records": 0,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None
        }
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as outfile:
            for i in range(count):
                # Generate synthetic profile
                profile = {
                    "id": i + 1,
                    "name": self.faker.name(),
                    "email": self.faker.email(),
                    "phone": self.faker.phone_number(),
                    "company": self.faker.company(),
                    "job_title": self.faker.job(),
                    "profile_text": self._generate_profile_text(),
                    "skills": self._generate_skills(),
                    "created_at": self.faker.date_time_between(start_date='-2y').isoformat(),
                    "pii_scrubbed": False,  # Will be processed by backfill
                    "anonymization_checksum": None
                }
                
                # Add checksum
                profile["anonymization_checksum"] = self._generate_checksum(profile)
                
                # Write record
                outfile.write(json.dumps(profile) + '\n')
                stats["generated_records"] += 1
                
                # Log progress
                if (i + 1) % 10000 == 0:
                    logger.info(f"Generated {i + 1:,} records...")
        
        stats["end_time"] = datetime.utcnow().isoformat()
        
        logger.info(f"Generation complete: {stats['generated_records']:,} records")
        
        return stats


def main():
    """Main data anonymization orchestration."""
    parser = argparse.ArgumentParser(description="Anonymize production data for staging")
    parser.add_argument(
        "--mode",
        choices=["anonymize", "generate"],
        required=True,
        help="Mode: anonymize existing data or generate synthetic data"
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Input data file (for anonymize mode)"
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        required=True,
        help="Output file path"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=250000,
        help="Target record count (default: 250,000)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--stats-file",
        type=Path,
        help="Path to save anonymization statistics"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.mode == "anonymize" and not args.input_file:
        parser.error("--input-file required for anonymize mode")
    
    # Initialize anonymizer
    anonymizer = DataAnonymizer(seed=args.seed)
    
    # Run anonymization or generation
    if args.mode == "anonymize":
        stats = anonymizer.anonymize_dataset(
            input_file=args.input_file,
            output_file=args.output_file,
            target_count=args.count
        )
    else:  # generate
        stats = anonymizer.generate_synthetic_data(
            output_file=args.output_file,
            count=args.count
        )
    
    # Save statistics
    if args.stats_file:
        args.stats_file.write_text(json.dumps(stats, indent=2))
        logger.info(f"Statistics saved to: {args.stats_file}")
    
    logger.info("Data anonymization complete!")


def _generate_profile_text(self) -> str:
    """Generate realistic profile text."""
    templates = [
        f"Experienced {self.faker.job()} with {random.randint(3, 15)} years in {self.faker.catch_phrase()}. "
        f"Proficient in various technologies and methodologies. Strong communication and leadership skills.",
        
        f"Results-driven professional specializing in {self.faker.bs()}. "
        f"Track record of delivering high-quality solutions. Team player with excellent problem-solving abilities.",
        
        f"Dedicated {self.faker.job()} passionate about {self.faker.catch_phrase()}. "
        f"Proven ability to manage complex projects and drive innovation.",
    ]
    
    return random.choice(templates)


def _generate_skills(self) -> List[str]:
    """Generate realistic skill set."""
    skill_pool = [
        "Python", "Java", "JavaScript", "TypeScript", "React", "Angular",
        "Node.js", "SQL", "NoSQL", "AWS", "Azure", "Docker", "Kubernetes",
        "Machine Learning", "Data Analysis", "Project Management", "Agile",
        "REST APIs", "GraphQL", "CI/CD", "Git", "Linux", "Communication"
    ]
    
    return random.sample(skill_pool, k=random.randint(5, 12))


# Monkey-patch methods into class
DataAnonymizer._generate_profile_text = _generate_profile_text
DataAnonymizer._generate_skills = _generate_skills


if __name__ == "__main__":
    main()
