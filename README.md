# Job Description to Candidate Skill Match System

This project is an AI-powered system that automates the process of matching internal team members (employees and contractors) to job requisitions within an organization. It uses a multi-AI agent approach to analyze job descriptions, match them against a database of team member skills and availability, and provide a ranked list of suitable candidates.

## Features

-   **RESTful API**: For submitting job requisitions and managing team member data.
-   **AI-Powered Matching**: Utilizes multiple AI agents for:
    -   JD Parsing and Normalization
    -   Skill Extraction and Normalization
    -   Skill Weighting and Scoring
    -   Availability and Experience Validation
    -   Ranking and Explanation
-   **Nightly Data Synchronization**: Keeps team member skills and availability up-to-date.
-   **Observability**: Structured logging and metrics for monitoring and traceability.
-   **Secure**: Authentication and authorization using OAuth2/JWT.

## Architecture

The system is designed as a backend service with a set of REST APIs. The core of the system is a processing pipeline built with AI agents (e.g., using LangChain) that orchestrates the matching process. The data is stored in a PostgreSQL database.

![System Architecture](input/InfoBeans%20JD%20Portal%20Skill-Matching%20System%20Architecture.png)

## Getting Started

### Prerequisites

-   Python 3.11+
-   PostgreSQL

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/ib-job-skill-match-system.git
    cd ib-job-skill-match-system
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    cd backend
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Set up the database:**
    -   Note: Database needs to be already create while import from pgAdmin
    -   Create a PostgreSQL database named `ib_job_skill_match_system`.
    -   Run the SQL script `input/ib-job-skill-match-system-db.sql` to create the tables.

4.  **Run the application:**
    ```bash
    uvicorn src.main:app --reload
    ```
    The application will be available at `http://127.0.0.1:8000`.

## API Documentation

### Main Endpoints

-   `POST /api/v1/job-skill-mapping`: Submits a new job requisition for matching.
-   `POST /api/v1/team-member-skill-availiability`: Ingests team member skills and availability data.
-   `GET /api/v1/job-skill-mapping`: Queries the results of a job match.
-   `GET /api/v1/health`: Health check endpoint.
-   `GET /api/v1/metrics`: Exposes Prometheus metrics.

For detailed request and response payloads, please refer to the `Revised Requisition Req-Resp and Team-Member-Skill-Availiability-PayLoad.pdf` document in the `input` directory.

## Database Schema



The database schema is defined in the `input/ib-job-skill-match-system-db.sql` file. The main tables are:

-   `requisition_requests`
-   `requisition_detail`
-   `team_member`
-   `skill_master`
-   `team_member_skill`
-   `team_member_allocation`
-   `requisition_team_member_match`

For a complete understanding of the schema, please refer to the SQL file.

