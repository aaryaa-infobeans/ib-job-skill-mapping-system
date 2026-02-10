-- Seed auth_clients table with test client for development
-- This is required for the requisition_requests foreign key constraint

-- Insert test client (using bcrypt hash for 'test-secret')
-- Hash generated with: python -c "from passlib.hash import bcrypt; print(bcrypt.hash('test-secret'))"
INSERT INTO auth_clients (client_name, client_code, client_secret_hash, auth_type, is_active) 
VALUES (
  'Test Client',
  'test-client',
  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVqP9b0Qm',  -- hash of 'test-secret'
  'OAUTH',
  true
)
ON CONFLICT (client_code) DO UPDATE 
SET 
  client_name = EXCLUDED.client_name,
  client_secret_hash = EXCLUDED.client_secret_hash,
  is_active = EXCLUDED.is_active,
  auth_type = EXCLUDED.auth_type;

-- Display inserted client
SELECT id, client_name, client_code, auth_type, is_active, created_at 
FROM auth_clients 
WHERE client_code = 'test-client';
