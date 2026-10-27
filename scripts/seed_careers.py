"""Seed the curated career knowledge database.

Populates the careers, career_skills, career_tools, career_projects, and
career_sources tables with a small, deterministic, sourced dataset.

All data is curated from public occupational sources (O*NET, U.S. Bureau of
Labor Statistics, official technology documentation, and recognized industry
references). The seed is idempotent: running it multiple times must not create
duplicates.

Usage:
    cd apps/api
    python ../scripts/seed_careers.py   # requires DATABASE_URL in .env
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, select

from app.core.database import create_all, get_engine, get_session_factory
from app.models.career import (
    Career,
    CareerProject,
    CareerSkill,
    CareerSource,
    CareerTool,
)

CAREER_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def deterministic_id(career_slug: str, suffix: str = "") -> uuid.UUID:
    """Return a stable UUID v5 derived from the career slug and an optional suffix."""
    name = f"{career_slug}:{suffix}" if suffix else career_slug
    return uuid.uuid5(CAREER_NAMESPACE, name)


# ---------------------------------------------------------------------------
# Career data: 8 curated profiles
# ---------------------------------------------------------------------------

CAREERS = [
    {
        "slug": "software-engineer",
        "title": "Software Engineer",
        "domain": "Software Development",
        "summary": "Designs, builds, tests, and maintains software applications and systems.",
        "description": (
            "Software engineers apply engineering principles to software creation. "
            "They work across the full development lifecycle — from requirements and "
            "design to implementation, testing, deployment, and maintenance — using "
            "programming languages, tools, and methodologies appropriate to the domain."
        ),
        "education_expectations": {
            "typical": "Bachelor's degree in Computer Science, Software Engineering, or a related field",
            "alternatives": [
                "Associate degree with relevant experience",
                "Bootcamp certificate with demonstrated portfolio",
                "Self-taught with strong project evidence",
            ],
            "mandatory": False,
        },
        "experience_expectations": {
            "entry_level": "0-2 years of professional software development",
            "mid_level": "2-5 years with increasing ownership of features or services",
            "senior_level": "5+ years with system design and mentorship responsibilities",
            "mandatory": False,
        },
        "skills": [
            ("Python", "Programming Language", "CORE", "INTERMEDIATE", "General-purpose programming language used for backend services, scripting, and tooling."),
            ("JavaScript", "Programming Language", "CORE", "INTERMEDIATE", "Core language for frontend web development and increasingly for backend (Node.js)."),
            ("Java", "Programming Language", "IMPORTANT", "BEGINNER", "Widely used in enterprise backend systems and Android development."),
            ("SQL", "Database", "CORE", "INTERMEDIATE", "Query language for relational databases; essential for data-backed applications."),
            ("Git", "Version Control", "CORE", "BEGINNER", "Distributed version control system for tracking source code changes."),
            ("Testing", "Software Quality", "IMPORTANT", "BEGINNER", "Writing automated unit, integration, and end-to-end tests."),
            ("System Design", "Software Architecture", "IMPORTANT", "ADVANCED", "Designing scalable, reliable, and maintainable software systems."),
            ("Debugging", "Software Quality", "IMPORTANT", "INTERMEDIATE", "Identifying, isolating, and resolving defects in software."),
            ("Agile", "Methodology", "SUPPORTING", "BEGINNER", "Iterative software development practices (Scrum, Kanban)."),
            ("REST APIs", "Integration", "IMPORTANT", "INTERMEDIATE", "Designing and consuming RESTful web services."),
        ],
        "tools": [
            ("Git", "Version Control", "CORE"),
            ("Docker", "Containerization", "IMPORTANT"),
            ("AWS", "Cloud Platform", "IMPORTANT"),
            ("PostgreSQL", "Database", "IMPORTANT"),
            ("React", "Frontend Framework", "IMPORTANT"),
            ("pytest", "Testing Framework", "IMPORTANT"),
            ("Linux CLI", "Operating System", "CORE"),
            ("VS Code", "Code Editor", "SUPPORTING"),
        ],
        "projects": [
            (
                "Full-Stack Application",
                "Build and deploy a web application with a database backend, user authentication, and a frontend interface.",
                ["Python", "JavaScript", "SQL", "REST APIs", "Git"],
                "Intermediate",
            ),
            (
                "API Service",
                "Design and implement a RESTful API with documentation, input validation, and automated tests.",
                ["Python", "SQL", "Testing", "REST APIs", "Git"],
                "Intermediate",
            ),
            (
                "CLI Tool",
                "Create a command-line utility that automates a repetitive task and handles errors gracefully.",
                ["Python", "Git", "Testing", "Debugging"],
                "Beginner",
            ),
        ],
        "sources": [
            (
                "Software Developers",
                "U.S. Bureau of Labor Statistics",
                "https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm",
                "government",
                date(2024, 4, 25),
                "high",
            ),
            (
                "Software Developers and Software Quality Assurance Analysts and Testers",
                "O*NET OnLine",
                "https://www.onetonline.org/link/summary/15-1252.00",
                "government",
                date(2024, 1, 1),
                "high",
            ),
        ],
    },
    {
        "slug": "data-analyst",
        "title": "Data Analyst",
        "domain": "Data & Analytics",
        "summary": "Collects, processes, and analyzes data to help organizations make informed decisions.",
        "description": (
            "Data analysts translate raw data into actionable insights. They clean and "
            "structure data, perform exploratory analysis, create visualizations, and "
            "communicate findings to stakeholders through dashboards and reports."
        ),
        "education_expectations": {
            "typical": "Bachelor's degree in Statistics, Mathematics, Economics, or a related quantitative field",
            "alternatives": [
                "Associate degree with demonstrated analytical experience",
                "Data analytics certificate with project portfolio",
            ],
            "mandatory": False,
        },
        "experience_expectations": {
            "entry_level": "0-2 years working with data in any capacity",
            "mid_level": "2-5 years producing recurring reports and dashboards for stakeholders",
        },
        "skills": [
            ("SQL", "Database", "CORE", "INTERMEDIATE", "Querying relational databases to extract and transform data."),
            ("Excel", "Spreadsheet", "CORE", "INTERMEDIATE", "Data manipulation, pivot tables, and basic modeling in Microsoft Excel or Google Sheets."),
            ("Tableau", "Visualization", "IMPORTANT", "BEGINNER", "Creating interactive dashboards and visualizations."),
            ("Python", "Programming Language", "IMPORTANT", "BEGINNER", "Data cleaning and analysis using pandas and related libraries."),
            ("Statistics", "Mathematics", "IMPORTANT", "BEGINNER", "Descriptive statistics, hypothesis testing, and interpreting results."),
            ("Data Visualization", "Communication", "IMPORTANT", "BEGINNER", "Presenting data insights through charts and graphs."),
            ("Power BI", "Visualization", "SUPPORTING", "BEGINNER", "Microsoft business analytics service for reports and dashboards."),
            ("R", "Programming Language", "SUPPORTING", "BEGINNER", "Statistical computing and graphics."),
        ],
        "tools": [
            ("SQL", "Database", "CORE"),
            ("Excel", "Spreadsheet", "CORE"),
            ("Tableau", "Visualization", "IMPORTANT"),
            ("Python", "Programming Language", "IMPORTANT"),
            ("Power BI", "Visualization", "SUPPORTING"),
            ("Git", "Version Control", "SUPPORTING"),
        ],
        "projects": [
            (
                "Sales Dashboard",
                "Build an interactive dashboard tracking sales performance by region, product, and time period.",
                ["SQL", "Tableau", "Data Visualization", "Excel"],
                "Intermediate",
            ),
            (
                "Customer Segmentation",
                "Analyze customer purchase data to identify distinct behavioral segments.",
                ["Python", "Statistics", "SQL", "Data Visualization"],
                "Intermediate",
            ),
            (
                "A/B Test Analysis",
                "Design and analyze the results of an online experiment, including significance testing.",
                ["Statistics", "SQL", "Python"],
                "Intermediate",
            ),
        ],
        "sources": [
            (
                "Data Scientists",
                "U.S. Bureau of Labor Statistics",
                "https://www.bls.gov/ooh/computer-and-information-technology/data-scientists.htm",
                "government",
                date(2024, 4, 25),
                "high",
            ),
            (
                "Data Scientists and Mathematical Science Occupations",
                "O*NET OnLine",
                "https://www.onetonline.org/link/summary/15-2051.00",
                "government",
                date(2024, 1, 1),
                "high",
            ),
        ],
    },
    {
        "slug": "data-scientist",
        "title": "Data Scientist",
        "domain": "Data & Analytics",
        "summary": "Applies statistical and machine learning techniques to extract insights and build predictive models from data.",
        "description": (
            "Data scientists go beyond descriptive analysis to build predictive models, "
            "run experiments, and develop algorithms. They combine domain knowledge with "
            "statistics, programming, and data engineering to solve complex problems."
        ),
        "education_expectations": {
            "typical": "Master's degree or PhD in Statistics, Computer Science, Mathematics, or a related quantitative field",
            "alternatives": [
                "Bachelor's degree with strong project portfolio and relevant experience",
            ],
            "mandatory": False,
        },
        "experience_expectations": {
            "entry_level": "0-2 years with academic or internship experience in modeling",
            "mid_level": "2-5 years deploying models and leading analysis projects",
        },
        "skills": [
            ("Python", "Programming Language", "CORE", "INTERMEDIATE", "Primary language for data manipulation and modeling (pandas, scikit-learn)."),
            ("SQL", "Database", "CORE", "INTERMEDIATE", "Extracting and joining data from relational databases."),
            ("Statistics", "Mathematics", "CORE", "INTERMEDIATE", "Inferential statistics, experimental design, and model validation."),
            ("Machine Learning", "Modeling", "CORE", "INTERMEDIATE", "Supervised and unsupervised learning algorithms."),
            ("Data Visualization", "Communication", "IMPORTANT", "BEGINNER", "Communicating model results and insights visually."),
            ("Feature Engineering", "Modeling", "IMPORTANT", "INTERMEDIATE", "Creating and selecting predictive features from raw data."),
            ("Model Evaluation", "Modeling", "IMPORTANT", "INTERMEDIATE", "Assessing model performance using appropriate metrics."),
            ("Experiment Design", "Methodology", "IMPORTANT", "BEGINNER", "Designing and analyzing A/B tests and controlled experiments."),
        ],
        "tools": [
            ("Python", "Programming Language", "CORE"),
            ("SQL", "Database", "CORE"),
            ("scikit-learn", "ML Library", "IMPORTANT"),
            ("Jupyter", "Development Environment", "IMPORTANT"),
            ("Tableau", "Visualization", "SUPPORTING"),
            ("Git", "Version Control", "SUPPORTING"),
        ],
        "projects": [
            (
                "Churn Prediction Model",
                "Build a classification model predicting customer churn from historical usage data.",
                ["Python", "Machine Learning", "SQL", "Feature Engineering", "Model Evaluation"],
                "Intermediate",
            ),
            (
                "Demand Forecasting",
                "Create a time-series model forecasting product demand for inventory planning.",
                ["Python", "Machine Learning", "Statistics", "SQL"],
                "Intermediate",
            ),
            (
                "Customer Segmentation",
                "Apply unsupervised learning to group customers by purchasing behavior.",
                ["Python", "Machine Learning", "Data Visualization"],
                "Beginner",
            ),
        ],
        "sources": [
            (
                "Data Scientists",
                "U.S. Bureau of Labor Statistics",
                "https://www.bls.gov/ooh/computer-and-information-technology/data-scientists.htm",
                "government",
                date(2024, 4, 25),
                "high",
            ),
            (
                "Data Scientists and Mathematical Science Occupations",
                "O*NET OnLine",
                "https://www.onetonline.org/link/summary/15-2051.00",
                "government",
                date(2024, 1, 1),
                "high",
            ),
        ],
    },
    {
        "slug": "machine-learning-engineer",
        "title": "Machine Learning Engineer",
        "domain": "Artificial Intelligence",
        "summary": "Builds, deploys, and maintains machine learning systems in production environments.",
        "description": (
            "ML engineers bridge data science and software engineering. They take "
            "prototype models and make them robust, scalable, and maintainable — handling "
            "feature pipelines, model serving, monitoring, and MLOps infrastructure."
        ),
        "education_expectations": {
            "typical": "Bachelor's or Master's degree in Computer Science, Mathematics, or a related field",
            "alternatives": [
                "Bachelor's with strong ML project portfolio",
            ],
            "mandatory": False,
        },
        "experience_expectations": {
            "entry_level": "0-2 years with ML coursework or internship experience",
            "mid_level": "2-5 years deploying models and building ML infrastructure",
        },
        "skills": [
            ("Python", "Programming Language", "CORE", "ADVANCED", "Primary language for ML implementation and pipeline code."),
            ("Machine Learning", "Modeling", "CORE", "INTERMEDIATE", "Supervised and unsupervised algorithms, model selection, and tuning."),
            ("Software Engineering", "Software Quality", "IMPORTANT", "INTERMEDIATE", "Writing production-quality, tested, and maintainable code."),
            ("SQL", "Database", "IMPORTANT", "INTERMEDIATE", "Querying data for training and feature pipelines."),
            ("MLOps", "Infrastructure", "IMPORTANT", "BEGINNER", "Model deployment, monitoring, and lifecycle management."),
            ("Docker", "Containerization", "IMPORTANT", "BEGINNER", "Containerizing ML models and training jobs."),
            ("Git", "Version Control", "CORE", "BEGINNER", "Version control for code and experiment tracking."),
        ],
        "tools": [
            ("Python", "Programming Language", "CORE"),
            ("scikit-learn", "ML Library", "CORE"),
            ("PyTorch", "ML Library", "IMPORTANT"),
            ("TensorFlow", "ML Library", "IMPORTANT"),
            ("Docker", "Containerization", "IMPORTANT"),
            ("AWS", "Cloud Platform", "IMPORTANT"),
            ("Git", "Version Control", "CORE"),
            ("MLflow", "MLOps", "SUPPORTING"),
        ],
        "projects": [
            (
                "ML Pipeline",
                "Build an end-to-end training pipeline that ingests data, trains a model, and evaluates it automatically.",
                ["Python", "Machine Learning", "SQL", "Git", "Docker"],
                "Intermediate",
            ),
            (
                "Model Deployment",
                "Deploy a trained model as a REST API with input validation and monitoring.",
                ["Python", "Machine Learning", "Software Engineering", "Docker"],
                "Intermediate",
            ),
            (
                "Feature Store",
                "Create a reusable feature computation pipeline for model training and inference.",
                ["Python", "SQL", "Software Engineering", "MLOps"],
                "Advanced",
            ),
        ],
        "sources": [
            (
                "Machine Learning Engineer",
                "O*NET OnLine",
                "https://www.onetonline.org/link/summary/15-1252.06",
                "government",
                date(2024, 1, 1),
                "high",
            ),
            (
                "Data Scientists",
                "U.S. Bureau of Labor Statistics",
                "https://www.bls.gov/ooh/computer-and-information-technology/data-scientists.htm",
                "government",
                date(2024, 4, 25),
                "high",
            ),
        ],
    },
    {
        "slug": "ai-engineer",
        "title": "AI Engineer",
        "domain": "Artificial Intelligence",
        "summary": "Builds applications powered by large language models and other foundation models.",
        "description": (
            "AI engineers apply pre-trained foundation models (including LLMs) to real "
            "world problems. They work on prompt engineering, retrieval-augmented "
            "generation (RAG), model fine-tuning, and integrating AI capabilities into "
            "software products."
        ),
        "education_expectations": {
            "typical": "Bachelor's degree in Computer Science or a related technical field",
            "alternatives": [
                "Demonstrated portfolio of LLM-powered applications",
            ],
            "mandatory": False,
        },
        "experience_expectations": {
            "entry_level": "0-2 years with AI/ML coursework or personal LLM projects",
            "mid_level": "2-5 years building and shipping AI-powered features",
        },
        "skills": [
            ("Python", "Programming Language", "CORE", "INTERMEDIATE", "Primary language for AI application development."),
            ("Large Language Models", "AI/ML", "CORE", "INTERMEDIATE", "Working with pre-trained LLMs, including prompt design and evaluation."),
            ("Prompt Engineering", "AI/ML", "IMPORTANT", "BEGINNER", "Designing effective prompts for foundation models."),
            ("Retrieval-Augmented Generation", "AI/ML", "IMPORTANT", "BEGINNER", "Combining LLMs with external knowledge retrieval."),
            ("Vector Databases", "Database", "IMPORTANT", "BEGINNER", "Storing and querying embeddings for semantic search."),
            ("APIs", "Integration", "IMPORTANT", "INTERMEDIATE", "Consuming model APIs (OpenAI, Anthropic, etc.) and exposing AI features."),
            ("Git", "Version Control", "CORE", "BEGINNER", "Version control for AI application code."),
        ],
        "tools": [
            ("Python", "Programming Language", "CORE"),
            ("LangChain", "AI Framework", "IMPORTANT"),
            ("OpenAI API", "Model API", "IMPORTANT"),
            ("Pinecone", "Vector Database", "IMPORTANT"),
            ("Docker", "Containerization", "SUPPORTING"),
            ("Git", "Version Control", "CORE"),
        ],
        "projects": [
            (
                "RAG Chatbot",
                "Build a chatbot that answers questions over a private document collection using retrieval-augmented generation.",
                ["Python", "Large Language Models", "Retrieval-Augmented Generation", "Vector Databases", "APIs"],
                "Intermediate",
            ),
            (
                "LLM Evaluation Harness",
                "Create a framework for comparing model outputs across multiple prompts and scoring them automatically.",
                ["Python", "Prompt Engineering", "Large Language Models", "APIs"],
                "Intermediate",
            ),
            (
                "Fine-Tuned Model",
                "Fine-tune a smaller language model on a domain-specific dataset and evaluate improvements.",
                ["Python", "Large Language Models", "APIs"],
                "Advanced",
            ),
        ],
        "sources": [
            (
                "Artificial Intelligence",
                "O*NET OnLine",
                "https://www.onetonline.org/find/quick?s=AI",
                "government",
                date(2024, 1, 1),
                "medium",
            ),
            (
                "Prompt Engineering Guide",
                "PromptingGuide.ai",
                "https://www.promptingguide.ai/",
                "industry",
                date(2024, 6, 1),
                "medium",
            ),
        ],
    },
    {
        "slug": "cybersecurity-analyst",
        "title": "Cybersecurity Analyst",
        "domain": "Security",
        "summary": "Protects organizational systems and data by monitoring, detecting, and responding to security threats.",
        "description": (
            "Cybersecurity analysts defend information systems against cyber threats. "
            "They monitor security events, investigate incidents, manage vulnerabilities, "
            "and help implement security controls across networks, endpoints, and applications."
        ),
        "education_expectations": {
            "typical": "Bachelor's degree in Cybersecurity, Computer Science, or Information Technology",
            "alternatives": [
                "Industry certifications (CompTIA Security+, CISSP) with relevant experience",
            ],
            "mandatory": False,
        },
        "experience_expectations": {
            "entry_level": "0-2 years in IT support, help desk, or junior security role",
            "mid_level": "2-5 years monitoring and responding to security incidents",
        },
        "skills": [
            ("Network Security", "Security", "CORE", "INTERMEDIATE", "Securing network infrastructure and monitoring network traffic."),
            ("Incident Response", "Security", "CORE", "INTERMEDIATE", "Detecting, analyzing, and responding to security incidents."),
            ("Vulnerability Management", "Security", "IMPORTANT", "BEGINNER", "Identifying, assessing, and remediating security vulnerabilities."),
            ("SIEM", "Security Tools", "IMPORTANT", "BEGINNER", "Using security information and event management tools for monitoring."),
            ("Python", "Programming Language", "SUPPORTING", "BEGINNER", "Scripting for automation and security tooling."),
            ("Linux", "Operating System", "IMPORTANT", "INTERMEDIATE", "Administering and securing Linux-based systems."),
            ("Risk Assessment", "Security", "IMPORTANT", "BEGINNER", "Evaluating security risks and recommending mitigations."),
            ("Compliance", "Governance", "SUPPORTING", "BEGINNER", "Understanding regulatory frameworks (HIPAA, PCI-DSS, GDPR)."),
        ],
        "tools": [
            ("SIEM", "Security Tools", "CORE"),
            ("Python", "Programming Language", "SUPPORTING"),
            ("Linux", "Operating System", "IMPORTANT"),
            ("Wireshark", "Network Analysis", "IMPORTANT"),
            ("Nessus", "Vulnerability Scanning", "IMPORTANT"),
            ("Git", "Version Control", "SUPPORTING"),
        ],
        "projects": [
            (
                "Incident Response Playbook",
                "Document and simulate a response to a simulated phishing or malware incident.",
                ["Incident Response", "Network Security", "Python"],
                "Intermediate",
            ),
            (
                "Vulnerability Scan",
                "Run and interpret a vulnerability scan against a test environment, then prioritize remediation.",
                ["Vulnerability Management", "Nessus", "Network Security"],
                "Beginner",
            ),
            (
                "Security Monitoring Dashboard",
                "Configure SIEM alerts and dashboards for suspicious login and access patterns.",
                ["SIEM", "Linux", "Network Security"],
                "Intermediate",
            ),
        ],
        "sources": [
            (
                "Information Security Analysts",
                "U.S. Bureau of Labor Statistics",
                "https://www.bls.gov/ooh/computer-and-information-technology/information-security-analysts.htm",
                "government",
                date(2024, 4, 25),
                "high",
            ),
            (
                "Information Security Analysts",
                "O*NET OnLine",
                "https://www.onetonline.org/link/summary/15-1212.00",
                "government",
                date(2024, 1, 1),
                "high",
            ),
        ],
    },
    {
        "slug": "cloud-devops-engineer",
        "title": "Cloud / DevOps Engineer",
        "domain": "Infrastructure",
        "summary": "Designs, builds, and maintains cloud infrastructure and deployment pipelines.",
        "description": (
            "Cloud and DevOps engineers manage the infrastructure that runs software "
            "applications. They provision cloud resources, automate deployments with CI/CD "
            "pipelines, manage container orchestration, and ensure system reliability and "
            "scalability."
        ),
        "education_expectations": {
            "typical": "Bachelor's degree in Computer Science, Information Technology, or a related field",
            "alternatives": [
                "Cloud certifications (AWS, Azure, GCP) with hands-on experience",
            ],
            "mandatory": False,
        },
        "experience_expectations": {
            "entry_level": "0-2 years in system administration or cloud support",
            "mid_level": "2-5 years managing cloud infrastructure and CI/CD pipelines",
        },
        "skills": [
            ("AWS", "Cloud Platform", "CORE", "INTERMEDIATE", "Amazon Web Services core services (EC2, S3, IAM, Lambda)."),
            ("Docker", "Containerization", "CORE", "INTERMEDIATE", "Containerizing applications for consistent deployment."),
            ("Kubernetes", "Container Orchestration", "IMPORTANT", "BEGINNER", "Managing containerized workloads at scale."),
            ("CI/CD", "Infrastructure", "IMPORTANT", "BEGINNER", "Building and maintaining continuous integration and deployment pipelines."),
            ("Terraform", "Infrastructure as Code", "IMPORTANT", "BEGINNER", "Provisioning infrastructure declaratively."),
            ("Linux", "Operating System", "CORE", "INTERMEDIATE", "Administering Linux servers and cloud instances."),
            ("Python", "Programming Language", "SUPPORTING", "BEGINNER", "Scripting infrastructure automation."),
            ("Monitoring", "Operations", "IMPORTANT", "BEGINNER", "Observability, alerting, and incident response for infrastructure."),
        ],
        "tools": [
            ("AWS", "Cloud Platform", "CORE"),
            ("Docker", "Containerization", "CORE"),
            ("Kubernetes", "Container Orchestration", "IMPORTANT"),
            ("Terraform", "Infrastructure as Code", "IMPORTANT"),
            ("GitHub Actions", "CI/CD", "IMPORTANT"),
            ("Linux", "Operating System", "CORE"),
            ("Python", "Programming Language", "SUPPORTING"),
        ],
        "projects": [
            (
                "Infrastructure as Code",
                "Provision a complete cloud environment (VPC, compute, storage) using Terraform.",
                ["Terraform", "AWS", "Linux"],
                "Intermediate",
            ),
            (
                "CI/CD Pipeline",
                "Build a pipeline that builds, tests, and deploys an application to the cloud on every code change.",
                ["CI/CD", "GitHub Actions", "Docker", "AWS"],
                "Intermediate",
            ),
            (
                "Kubernetes Deployment",
                "Deploy a multi-service application to a Kubernetes cluster with rolling updates.",
                ["Docker", "Kubernetes", "AWS", "Linux"],
                "Intermediate",
            ),
        ],
        "sources": [
            (
                "Network and Computer Systems Administrators",
                "U.S. Bureau of Labor Statistics",
                "https://www.bls.gov/ooh/computer-and-information-technology/network-and-computer-systems-administrators.htm",
                "government",
                date(2024, 4, 25),
                "high",
            ),
            (
                "Cloud Engineers",
                "O*NET OnLine",
                "https://www.onetonline.org/find/quick?s=cloud",
                "government",
                date(2024, 1, 1),
                "medium",
            ),
        ],
    },
    {
        "slug": "product-analyst",
        "title": "Product Analyst",
        "domain": "Product Management",
        "summary": "Uses data to inform product decisions, measure feature impact, and guide product strategy.",
        "description": (
            "Product analysts work at the intersection of data, product, and business. "
            "They define success metrics, analyze user behavior, run experiments, and "
            "help product managers prioritize features based on evidence."
        ),
        "education_expectations": {
            "typical": "Bachelor's degree in Business, Economics, Statistics, or a related field",
            "alternatives": [
                "Demonstrated analytical portfolio with product metrics",
            ],
            "mandatory": False,
        },
        "experience_expectations": {
            "entry_level": "0-2 years in data analysis, business analysis, or product support",
            "mid_level": "2-5 years owning product metrics and experiment programs",
        },
        "skills": [
            ("SQL", "Database", "CORE", "INTERMEDIATE", "Querying product and user data to answer business questions."),
            ("Product Metrics", "Product Management", "CORE", "BEGINNER", "Defining and tracking KPIs such as activation, retention, and conversion."),
            ("A/B Testing", "Methodology", "IMPORTANT", "BEGINNER", "Designing and analyzing product experiments."),
            ("Data Visualization", "Communication", "IMPORTANT", "BEGINNER", "Creating dashboards that communicate product performance."),
            ("Statistics", "Mathematics", "IMPORTANT", "BEGINNER", "Interpreting statistical significance and avoiding common analytical errors."),
            ("Excel", "Spreadsheet", "IMPORTANT", "INTERMEDIATE", "Quick analysis and ad-hoc reporting."),
            ("Python", "Programming Language", "SUPPORTING", "BEGINNER", "Automating repetitive data pulls and analyses."),
            ("User Research", "Product Management", "SUPPORTING", "BEGINNER", "Combining quantitative data with qualitative user insights."),
        ],
        "tools": [
            ("SQL", "Database", "CORE"),
            ("Excel", "Spreadsheet", "IMPORTANT"),
            ("Tableau", "Visualization", "IMPORTANT"),
            ("Python", "Programming Language", "SUPPORTING"),
            ("Amplitude", "Product Analytics", "SUPPORTING"),
            ("Git", "Version Control", "SUPPORTING"),
        ],
        "projects": [
            (
                "Product Metrics Dashboard",
                "Build a dashboard tracking activation, retention, and conversion for a digital product.",
                ["SQL", "Tableau", "Product Metrics", "Excel"],
                "Intermediate",
            ),
            (
                "Feature Impact Analysis",
                "Measure the effect of a new feature using pre/post analysis and segment breakdowns.",
                ["SQL", "Statistics", "Product Metrics", "Python"],
                "Intermediate",
            ),
            (
                "A/B Test Program",
                "Design, run, and analyze a product experiment with clear success criteria.",
                ["A/B Testing", "Statistics", "SQL"],
                "Intermediate",
            ),
        ],
        "sources": [
            (
                "Management Analysts",
                "U.S. Bureau of Labor Statistics",
                "https://www.bls.gov/ooh/business-and-financial/management-analysts.htm",
                "government",
                date(2024, 4, 25),
                "medium",
            ),
            (
                "Product Management",
                "O*NET OnLine",
                "https://www.onetonline.org/find/quick?s=product",
                "government",
                date(2024, 1, 1),
                "medium",
            ),
        ],
    },
]


def build_seed_data() -> dict:
    """Build the complete seed data structure from the CAREERS definition."""
    careers = []
    all_skills = []
    all_tools = []
    all_projects = []
    all_sources = []

    for career_data in CAREERS:
        cid = deterministic_id(career_data["slug"])
        careers.append({
            "id": cid,
            "slug": career_data["slug"],
            "title": career_data["title"],
            "domain": career_data["domain"],
            "summary": career_data["summary"],
            "description": career_data["description"],
            "education_expectations": career_data["education_expectations"],
            "experience_expectations": career_data["experience_expectations"],
        })

        for skill_name, category, importance, level, desc in career_data["skills"]:
            all_skills.append({
                "id": deterministic_id(career_data["slug"], f"skill:{skill_name}"),
                "career_id": cid,
                "skill_name": skill_name,
                "category": category,
                "importance": importance,
                "minimum_level": level,
                "description": desc,
            })

        for tool_name, category, importance in career_data["tools"]:
            all_tools.append({
                "id": deterministic_id(career_data["slug"], f"tool:{tool_name}"),
                "career_id": cid,
                "tool_name": tool_name,
                "category": category,
                "importance": importance,
            })

        for proj_type, desc, skills_demo, difficulty in career_data["projects"]:
            all_projects.append({
                "id": deterministic_id(career_data["slug"], f"project:{proj_type}"),
                "career_id": cid,
                "project_type": proj_type,
                "description": desc,
                "skills_demonstrated": skills_demo,
                "difficulty": difficulty,
            })

        for idx, (title, publisher, url, source_type, published, reliability) in enumerate(career_data["sources"]):
            all_sources.append({
                "id": deterministic_id(career_data["slug"], f"source:{idx}"),
                "career_id": cid,
                "title": title,
                "publisher": publisher,
                "url": url,
                "source_type": source_type,
                "published_at": published,
                "retrieved_at": datetime.now(timezone.utc),
                "reliability": reliability,
            })

    return {
        "careers": careers,
        "skills": all_skills,
        "tools": all_tools,
        "projects": all_projects,
        "sources": all_sources,
    }


async def seed(session) -> None:
    """Insert or update career knowledge data idempotently."""
    data = build_seed_data()

    # Upsert careers
    for career in data["careers"]:
        existing = (await session.execute(
            select(Career).where(Career.slug == career["slug"])
        )).scalar_one_or_none()
        if existing:
            existing.title = career["title"]
            existing.domain = career["domain"]
            existing.summary = career["summary"]
            existing.description = career["description"]
            existing.education_expectations = career["education_expectations"]
            existing.experience_expectations = career["experience_expectations"]
        else:
            session.add(Career(**career))
    await session.commit()

    # Helper to upsert child records by unique key
    async def upsert_child(model, career_id, unique_fields, defaults):
        existing = (await session.execute(
            select(model).where(
                and_(*(getattr(model, k) == v for k, v in unique_fields.items()))
            )
        )).scalar_one_or_none()
        if existing:
            for k, v in defaults.items():
                setattr(existing, k, v)
        else:
            session.add(model(career_id=career_id, **unique_fields, **defaults))

    # Upsert skills
    for skill in data["skills"]:
        career = next(c for c in data["careers"] if c["id"] == skill["career_id"])
        await upsert_child(
            CareerSkill,
            career["id"],
            {"skill_name": skill["skill_name"]},
            {
                "category": skill["category"],
                "importance": skill["importance"],
                "minimum_level": skill["minimum_level"],
                "description": skill["description"],
            },
        )

    # Upsert tools
    for tool in data["tools"]:
        career = next(c for c in data["careers"] if c["id"] == tool["career_id"])
        await upsert_child(
            CareerTool,
            career["id"],
            {"tool_name": tool["tool_name"]},
            {
                "category": tool["category"],
                "importance": tool["importance"],
            },
        )

    # Upsert projects
    for project in data["projects"]:
        career = next(c for c in data["careers"] if c["id"] == project["career_id"])
        await upsert_child(
            CareerProject,
            career["id"],
            {"project_type": project["project_type"]},
            {
                "description": project["description"],
                "skills_demonstrated": project["skills_demonstrated"],
                "difficulty": project["difficulty"],
            },
        )

    # Upsert sources
    for source in data["sources"]:
        career = next(c for c in data["careers"] if c["id"] == source["career_id"])
        await upsert_child(
            CareerSource,
            career["id"],
            {"title": source["title"]},
            {
                "publisher": source["publisher"],
                "url": source["url"],
                "source_type": source["source_type"],
                "published_at": source["published_at"],
                "retrieved_at": source["retrieved_at"],
                "reliability": source["reliability"],
            },
        )

    await session.commit()


async def main() -> None:
    await create_all()
    factory = get_session_factory()
    async with factory() as session:
        await seed(session)
        data = build_seed_data()
        print("Career knowledge seed complete.")
        print(f"  Careers: {len(data['careers'])}")
        print(f"  Skills: {len(data['skills'])}")
        print(f"  Tools: {len(data['tools'])}")
        print(f"  Projects: {len(data['projects'])}")
        print(f"  Sources: {len(data['sources'])}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
