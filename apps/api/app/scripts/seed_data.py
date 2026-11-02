"""Curated reference data definitions for CareerTwin seed system.

All data is deterministic and keyed by stable identifiers (slugs for careers,
names for skills/resources/questions) to support idempotent upserts.

Source/provenance metadata is preserved for every record.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Canonical skill names (must match skill_normalization aliases)
# ---------------------------------------------------------------------------

SKILL_PYTHON = "Python"
SKILL_SQL = "SQL"
SKILL_JAVASCRIPT = "JavaScript"
SKILL_TYPESCRIPT = "TypeScript"
SKILL_JAVA = "Java"
SKILL_REACT = "React"
SKILL_NODE = "Node.js"
SKILL_AWS = "AWS"
SKILL_GCP = "GCP"
SKILL_AZURE = "Azure"
SKILL_DOCKER = "Docker"
SKILL_KUBERNETES = "Kubernetes"
SKILL_GIT = "Git"
SKILL_LINUX = "Linux"
SKILL_REST_API = "REST API"
SKILL_GRAPHQL = "GraphQL"
SKILL_MACHINE_LEARNING = "Machine Learning"
SKILL_DEEP_LEARNING = "Deep Learning"
SKILL_NLP = "Natural Language Processing"
SKILL_COMPUTER_VISION = "Computer Vision"
SKILL_PROMPT_ENGINEERING = "Prompt Engineering"
SKILL_RAG = "Retrieval-Augmented Generation"
SKILL_PANDAS = "Pandas"
SKILL_NUMPY = "NumPy"
SKILL_SCIKIT_LEARN = "scikit-learn"
SKILL_TENSORFLOW = "TensorFlow"
SKILL_PYTORCH = "PyTorch"
SKILL_TABLEAU = "Tableau"
SKILL_POWER_BI = "Power BI"
SKILL_EXCEL = "Excel"
SKILL_STATISTICS = "Statistics"
SKILL_PROBABILITY = "Probability"
SKILL_LINEAR_ALGEBRA = "Linear Algebra"
SKILL_CALCULUS = "Calculus"
SKILL_MONGODB = "MongoDB"
SKILL_POSTGRESQL = "PostgreSQL"
SKILL_REDIS = "Redis"

SKILL_LLM = "Large Language Models"

SKILL_NETWORK_SECURITY = "Network Security"

# ---------------------------------------------------------------------------
# Career definitions (8 careers)
# Each career has: slug, title, domain, summary, description,
# education_expectations, experience_expectations, skills, tools, projects, sources
# ---------------------------------------------------------------------------

CAREERS: list[dict[str, Any]] = [
    {
        "slug": "software-engineer",
        "title": "Software Engineer",
        "domain": "Engineering",
        "summary": "Designs, develops, tests, and maintains software applications and systems.",
        "description": "Software Engineers build applications using programming languages, frameworks, and tools. They work across the full development lifecycle from design to deployment.",
        "education_expectations": {"typical": "Bachelor's degree in Computer Science or related field"},
        "experience_expectations": {"entry_level": "0-2 years", "mid_level": "3-5 years"},
        "skills": [
            {"skill_name": SKILL_PYTHON, "category": "Programming Language", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Core programming language for backend and scripting"},
            {"skill_name": SKILL_JAVASCRIPT, "category": "Programming Language", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Frontend and full-stack development"},
            {"skill_name": SKILL_GIT, "category": "Version Control", "importance": "CORE", "minimum_level": "BEGINNER", "description": "Version control and collaboration"},
            {"skill_name": SKILL_SQL, "category": "Database", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Relational database queries"},
            {"skill_name": SKILL_REST_API, "category": "API Design", "importance": "IMPORTANT", "minimum_level": "INTERMEDIATE", "description": "RESTful API design and implementation"},
            {"skill_name": SKILL_DOCKER, "category": "DevOps", "importance": "SUPPORTING", "minimum_level": "BEGINNER", "description": "Containerization"},
            {"skill_name": SKILL_AWS, "category": "Cloud", "importance": "SUPPORTING", "minimum_level": "BEGINNER", "description": "Cloud platform services"},
        ],
        "tools": [
            {"tool_name": "Git", "category": "Version Control", "importance": "CORE"},
            {"tool_name": "Docker", "category": "Containerization", "importance": "IMPORTANT"},
            {"tool_name": "AWS", "category": "Cloud Platform", "importance": "SUPPORTING"},
            {"tool_name": "PostgreSQL", "category": "Database", "importance": "IMPORTANT"},
        ],
        "projects": [
            {
                "project_type": "Capstone",
                "description": "Build a full-stack web application with React frontend and Python backend",
                "skills_demonstrated": [SKILL_PYTHON, SKILL_JAVASCRIPT, SKILL_REST_API, SKILL_SQL],
                "difficulty": "Intermediate",
            },
            {
                "project_type": "Personal",
                "description": "CI/CD pipeline with Docker and AWS deployment",
                "skills_demonstrated": [SKILL_DOCKER, SKILL_AWS, SKILL_GIT],
                "difficulty": "Advanced",
            },
        ],
        "sources": [
            {
                "title": "O*NET - Software Developers",
                "publisher": "U.S. Department of Labor",
                "url": "https://www.onetonline.org/link/summary/15-1252.00",
                "source_type": "government",
                "reliability": "high",
            },
            {
                "title": "BLS - Software Developer Outlook",
                "publisher": "U.S. Bureau of Labor Statistics",
                "url": "https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm",
                "source_type": "government",
                "reliability": "high",
            },
        ],
    },
    {
        "slug": "data-analyst",
        "title": "Data Analyst",
        "domain": "Data",
        "summary": "Collects, processes, and analyzes data to help organizations make informed decisions.",
        "description": "Data Analysts work with data to identify trends, create visualizations, and produce reports that support business decision-making.",
        "education_expectations": {"typical": "Bachelor's degree in Mathematics, Statistics, or related field"},
        "experience_expectations": {"entry_level": "0-2 years", "mid_level": "3-5 years"},
        "skills": [
            {"skill_name": SKILL_SQL, "category": "Database", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Complex SQL queries and data extraction"},
            {"skill_name": SKILL_PYTHON, "category": "Programming Language", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Data manipulation and analysis"},
            {"skill_name": SKILL_EXCEL, "category": "Spreadsheet", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Advanced spreadsheet analysis"},
            {"skill_name": SKILL_TABLEAU, "category": "Visualization", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Data visualization and dashboards"},
            {"skill_name": SKILL_POWER_BI, "category": "Visualization", "importance": "SUPPORTING", "minimum_level": "BEGINNER", "description": "Business intelligence dashboards"},
            {"skill_name": SKILL_STATISTICS, "category": "Mathematics", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Statistical analysis and inference"},
        ],
        "tools": [
            {"tool_name": "SQL", "category": "Database", "importance": "CORE"},
            {"tool_name": "Python", "category": "Programming Language", "importance": "CORE"},
            {"tool_name": "Tableau", "category": "Visualization", "importance": "IMPORTANT"},
            {"tool_name": "Excel", "category": "Spreadsheet", "importance": "CORE"},
        ],
        "projects": [
            {
                "project_type": "Capstone",
                "description": "End-to-end data analysis project with SQL, Python, and Tableau",
                "skills_demonstrated": [SKILL_SQL, SKILL_PYTHON, SKILL_TABLEAU, SKILL_STATISTICS],
                "difficulty": "Intermediate",
            },
        ],
        "sources": [
            {
                "title": "O*NET - Data Scientists",
                "publisher": "U.S. Department of Labor",
                "url": "https://www.onetonline.org/link/summary/15-2051.00",
                "source_type": "government",
                "reliability": "high",
            },
        ],
    },
    {
        "slug": "data-scientist",
        "title": "Data Scientist",
        "domain": "Data",
        "summary": "Applies statistical and machine learning techniques to extract insights from data.",
        "description": "Data Scientists build predictive models, run experiments, and translate data into business recommendations.",
        "education_expectations": {"typical": "Master's degree in Data Science, Statistics, or related field"},
        "experience_expectations": {"entry_level": "0-2 years", "mid_level": "3-5 years"},
        "skills": [
            {"skill_name": SKILL_PYTHON, "category": "Programming Language", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Primary language for data science"},
            {"skill_name": SKILL_SQL, "category": "Database", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Data extraction and manipulation"},
            {"skill_name": SKILL_MACHINE_LEARNING, "category": "Machine Learning", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Supervised and unsupervised learning"},
            {"skill_name": SKILL_STATISTICS, "category": "Mathematics", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Statistical testing and inference"},
            {"skill_name": SKILL_PANDAS, "category": "Data Manipulation", "importance": "IMPORTANT", "minimum_level": "INTERMEDIATE", "description": "DataFrame-based analysis"},
            {"skill_name": SKILL_NUMPY, "category": "Data Manipulation", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Numerical computing"},
            {"skill_name": SKILL_SCIKIT_LEARN, "category": "Machine Learning", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "ML model implementation"},
        ],
        "tools": [
            {"tool_name": "Python", "category": "Programming Language", "importance": "CORE"},
            {"tool_name": "SQL", "category": "Database", "importance": "CORE"},
            {"tool_name": "scikit-learn", "category": "ML Library", "importance": "IMPORTANT"},
            {"tool_name": "Pandas", "category": "Data Library", "importance": "IMPORTANT"},
        ],
        "projects": [
            {
                "project_type": "Capstone",
                "description": "Predictive modeling project with scikit-learn and statistical validation",
                "skills_demonstrated": [SKILL_PYTHON, SKILL_MACHINE_LEARNING, SKILL_STATISTICS, SKILL_SCIKIT_LEARN],
                "difficulty": "Advanced",
            },
        ],
        "sources": [
            {
                "title": "O*NET - Data Scientists",
                "publisher": "U.S. Department of Labor",
                "url": "https://www.onetonline.org/link/summary/15-2051.00",
                "source_type": "government",
                "reliability": "high",
            },
        ],
    },
    {
        "slug": "machine-learning-engineer",
        "title": "Machine Learning Engineer",
        "domain": "Engineering",
        "summary": "Builds and deploys machine learning models into production systems.",
        "description": "ML Engineers bridge data science and software engineering, putting models into production with scalable infrastructure.",
        "education_expectations": {"typical": "Master's degree in Computer Science, ML, or related field"},
        "experience_expectations": {"entry_level": "0-2 years", "mid_level": "3-5 years"},
        "skills": [
            {"skill_name": SKILL_PYTHON, "category": "Programming Language", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Primary ML engineering language"},
            {"skill_name": SKILL_MACHINE_LEARNING, "category": "Machine Learning", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "ML algorithms and model training"},
            {"skill_name": SKILL_DEEP_LEARNING, "category": "Machine Learning", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Neural networks and deep architectures"},
            {"skill_name": SKILL_TENSORFLOW, "category": "ML Framework", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "TensorFlow model development"},
            {"skill_name": SKILL_PYTORCH, "category": "ML Framework", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "PyTorch model development"},
            {"skill_name": SKILL_DOCKER, "category": "DevOps", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Containerizing ML models"},
            {"skill_name": SKILL_AWS, "category": "Cloud", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Cloud ML infrastructure"},
        ],
        "tools": [
            {"tool_name": "Python", "category": "Programming Language", "importance": "CORE"},
            {"tool_name": "TensorFlow", "category": "ML Framework", "importance": "IMPORTANT"},
            {"tool_name": "PyTorch", "category": "ML Framework", "importance": "IMPORTANT"},
            {"tool_name": "Docker", "category": "Containerization", "importance": "IMPORTANT"},
            {"tool_name": "AWS", "category": "Cloud Platform", "importance": "IMPORTANT"},
        ],
        "projects": [
            {
                "project_type": "Capstone",
                "description": "ML model deployment pipeline with Docker and AWS",
                "skills_demonstrated": [SKILL_PYTHON, SKILL_MACHINE_LEARNING, SKILL_DOCKER, SKILL_AWS],
                "difficulty": "Advanced",
            },
        ],
        "sources": [
            {
                "title": "O*NET - Data Scientists",
                "publisher": "U.S. Department of Labor",
                "url": "https://www.onetonline.org/link/summary/15-2051.00",
                "source_type": "government",
                "reliability": "high",
            },
        ],
    },
    {
        "slug": "ai-engineer",
        "title": "AI Engineer",
        "domain": "Engineering",
        "summary": "Builds applications powered by large language models and generative AI.",
        "description": "AI Engineers integrate foundation models into applications using RAG, prompt engineering, and model fine-tuning.",
        "education_expectations": {"typical": "Bachelor's or Master's in Computer Science or related field"},
        "experience_expectations": {"entry_level": "0-2 years", "mid_level": "3-5 years"},
        "skills": [
            {"skill_name": SKILL_PYTHON, "category": "Programming Language", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Primary AI engineering language"},
            {"skill_name": SKILL_PROMPT_ENGINEERING, "category": "AI", "importance": "CORE", "minimum_level": "BEGINNER", "description": "Designing effective LLM prompts"},
            {"skill_name": SKILL_RAG, "category": "AI", "importance": "CORE", "minimum_level": "BEGINNER", "description": "Retrieval-augmented generation systems"},
            {"skill_name": SKILL_LLM, "category": "AI", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Working with foundation models"},
            {"skill_name": SKILL_REST_API, "category": "API Design", "importance": "IMPORTANT", "minimum_level": "INTERMEDIATE", "description": "APIs for AI services"},
            {"skill_name": SKILL_AWS, "category": "Cloud", "importance": "SUPPORTING", "minimum_level": "BEGINNER", "description": "Cloud AI services"},
        ],
        "tools": [
            {"tool_name": "Python", "category": "Programming Language", "importance": "CORE"},
            {"tool_name": "Docker", "category": "Containerization", "importance": "IMPORTANT"},
            {"tool_name": "AWS", "category": "Cloud Platform", "importance": "SUPPORTING"},
        ],
        "projects": [
            {
                "project_type": "Capstone",
                "description": "RAG-powered chat application with vector database",
                "skills_demonstrated": [SKILL_PYTHON, SKILL_PROMPT_ENGINEERING, SKILL_RAG, SKILL_REST_API],
                "difficulty": "Advanced",
            },
        ],
        "sources": [
            {
                "title": "O*NET - Computer Occupations",
                "publisher": "U.S. Department of Labor",
                "url": "https://www.onetonline.org/find/",
                "source_type": "government",
                "reliability": "medium",
            },
        ],
    },
    {
        "slug": "cybersecurity-analyst",
        "title": "Cybersecurity Analyst",
        "domain": "Security",
        "summary": "Protects organization's systems and data from cyber threats.",
        "description": "Cybersecurity Analysts monitor networks, respond to incidents, and implement security controls.",
        "education_expectations": {"typical": "Bachelor's degree in Cybersecurity or related field"},
        "experience_expectations": {"entry_level": "0-2 years", "mid_level": "3-5 years"},
        "skills": [
            {"skill_name": SKILL_LINUX, "category": "Operating System", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Linux system administration"},
            {"skill_name": SKILL_NETWORK_SECURITY, "category": "Security", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Network defense and monitoring"},
            {"skill_name": SKILL_SQL, "category": "Database", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Database security and forensics"},
            {"skill_name": SKILL_PYTHON, "category": "Programming Language", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Security scripting and automation"},
            {"skill_name": SKILL_AWS, "category": "Cloud", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Cloud security"},
        ],
        "tools": [
            {"tool_name": "Linux", "category": "Operating System", "importance": "CORE"},
            {"tool_name": "AWS", "category": "Cloud Platform", "importance": "IMPORTANT"},
            {"tool_name": "Python", "category": "Programming Language", "importance": "IMPORTANT"},
        ],
        "projects": [
            {
                "project_type": "Capstone",
                "description": "Network security monitoring and incident response lab",
                "skills_demonstrated": [SKILL_LINUX, SKILL_NETWORK_SECURITY, SKILL_PYTHON],
                "difficulty": "Intermediate",
            },
        ],
        "sources": [
            {
                "title": "O*NET - Information Security Analysts",
                "publisher": "U.S. Department of Labor",
                "url": "https://www.onetonline.org/link/summary/15-1212.00",
                "source_type": "government",
                "reliability": "high",
            },
        ],
    },
    {
        "slug": "cloud-devops-engineer",
        "title": "Cloud / DevOps Engineer",
        "domain": "Engineering",
        "summary": "Builds and maintains cloud infrastructure and CI/CD pipelines.",
        "description": "Cloud/DevOps Engineers automate infrastructure, manage cloud resources, and build deployment pipelines.",
        "education_expectations": {"typical": "Bachelor's degree in Computer Science or related field"},
        "experience_expectations": {"entry_level": "0-2 years", "mid_level": "3-5 years"},
        "skills": [
            {"skill_name": SKILL_AWS, "category": "Cloud", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Amazon Web Services"},
            {"skill_name": SKILL_DOCKER, "category": "DevOps", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Containerization"},
            {"skill_name": SKILL_KUBERNETES, "category": "DevOps", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Container orchestration"},
            {"skill_name": SKILL_GIT, "category": "Version Control", "importance": "CORE", "minimum_level": "BEGINNER", "description": "Version control"},
            {"skill_name": SKILL_LINUX, "category": "Operating System", "importance": "IMPORTANT", "minimum_level": "INTERMEDIATE", "description": "Linux administration"},
            {"skill_name": SKILL_REST_API, "category": "API Design", "importance": "SUPPORTING", "minimum_level": "BEGINNER", "description": "Infrastructure APIs"},
        ],
        "tools": [
            {"tool_name": "AWS", "category": "Cloud Platform", "importance": "CORE"},
            {"tool_name": "Docker", "category": "Containerization", "importance": "CORE"},
            {"tool_name": "Kubernetes", "category": "Orchestration", "importance": "IMPORTANT"},
            {"tool_name": "Git", "category": "Version Control", "importance": "CORE"},
        ],
        "projects": [
            {
                "project_type": "Capstone",
                "description": "CI/CD pipeline with Docker, Kubernetes, and AWS",
                "skills_demonstrated": [SKILL_DOCKER, SKILL_KUBERNETES, SKILL_AWS, SKILL_GIT],
                "difficulty": "Advanced",
            },
        ],
        "sources": [
            {
                "title": "O*NET - Computer Occupations",
                "publisher": "U.S. Department of Labor",
                "url": "https://www.onetonline.org/find/",
                "source_type": "government",
                "reliability": "medium",
            },
        ],
    },
    {
        "slug": "product-analyst",
        "title": "Product Analyst",
        "domain": "Product",
        "summary": "Analyzes product data to guide product decisions and strategy.",
        "description": "Product Analysts work with product teams to measure feature performance, analyze user behavior, and recommend improvements.",
        "education_expectations": {"typical": "Bachelor's degree in Business, Analytics, or related field"},
        "experience_expectations": {"entry_level": "0-2 years", "mid_level": "3-5 years"},
        "skills": [
            {"skill_name": SKILL_SQL, "category": "Database", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Product metrics and user behavior queries"},
            {"skill_name": SKILL_EXCEL, "category": "Spreadsheet", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Financial and product modeling"},
            {"skill_name": SKILL_TABLEAU, "category": "Visualization", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "Product dashboards"},
            {"skill_name": SKILL_POWER_BI, "category": "Visualization", "importance": "SUPPORTING", "minimum_level": "BEGINNER", "description": "Business intelligence"},
            {"skill_name": SKILL_STATISTICS, "category": "Mathematics", "importance": "IMPORTANT", "minimum_level": "BEGINNER", "description": "A/B testing and statistical significance"},
            {"skill_name": SKILL_PYTHON, "category": "Programming Language", "importance": "SUPPORTING", "minimum_level": "BEGINNER", "description": "Data automation"},
        ],
        "tools": [
            {"tool_name": "SQL", "category": "Database", "importance": "CORE"},
            {"tool_name": "Excel", "category": "Spreadsheet", "importance": "CORE"},
            {"tool_name": "Tableau", "category": "Visualization", "importance": "IMPORTANT"},
            {"tool_name": "Power BI", "category": "Visualization", "importance": "SUPPORTING"},
        ],
        "projects": [
            {
                "project_type": "Capstone",
                "description": "Product analytics dashboard with SQL and Tableau",
                "skills_demonstrated": [SKILL_SQL, SKILL_TABLEAU, SKILL_STATISTICS, SKILL_EXCEL],
                "difficulty": "Intermediate",
            },
        ],
        "sources": [
            {
                "title": "O*NET - Management Analysts",
                "publisher": "U.S. Department of Labor",
                "url": "https://www.onetonline.org/link/summary/13-1111.00",
                "source_type": "government",
                "reliability": "high",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Learning resource definitions (mapped to skills)
# ---------------------------------------------------------------------------

LEARNING_RESOURCES: list[dict[str, Any]] = [
    {
        "title": "Python for Everybody",
        "provider": "University of Michigan (Coursera)",
        "resource_type": "COURSE",
        "url": "https://www.coursera.org/specializations/python",
        "description": "Introductory Python programming course",
        "difficulty": "BEGINNER",
        "estimated_hours": 40.0,
        "skill_mappings": [
            {"skill_name": SKILL_PYTHON, "relevance_score": 0.95, "coverage_type": "COMPREHENSIVE"},
        ],
    },
    {
        "title": "SQL for Data Science",
        "provider": "UC Davis (Coursera)",
        "resource_type": "COURSE",
        "url": "https://www.coursera.org/learn/sql-for-data-science",
        "description": "SQL fundamentals for data analysis",
        "difficulty": "BEGINNER",
        "estimated_hours": 30.0,
        "skill_mappings": [
            {"skill_name": SKILL_SQL, "relevance_score": 0.95, "coverage_type": "COMPREHENSIVE"},
        ],
    },
    {
        "title": "Advanced SQL",
        "provider": "Mode Analytics",
        "resource_type": "TUTORIAL",
        "url": "https://mode.com/sql-tutorial/",
        "description": "Advanced SQL concepts including window functions and CTEs",
        "difficulty": "INTERMEDIATE",
        "estimated_hours": 20.0,
        "skill_mappings": [
            {"skill_name": SKILL_SQL, "relevance_score": 0.9, "coverage_type": "ADVANCED"},
        ],
    },
    {
        "title": "React Documentation",
        "provider": "Meta",
        "resource_type": "DOCUMENTATION",
        "url": "https://react.dev/",
        "description": "Official React documentation",
        "difficulty": "INTERMEDIATE",
        "estimated_hours": 25.0,
        "skill_mappings": [
            {"skill_name": SKILL_JAVASCRIPT, "relevance_score": 0.85, "coverage_type": "COMPREHENSIVE"},
        ],
    },
    {
        "title": "AWS Cloud Practitioner Essentials",
        "provider": "Amazon Web Services",
        "resource_type": "COURSE",
        "url": "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/",
        "description": "Introduction to AWS cloud services",
        "difficulty": "BEGINNER",
        "estimated_hours": 30.0,
        "skill_mappings": [
            {"skill_name": SKILL_AWS, "relevance_score": 0.95, "coverage_type": "COMPREHENSIVE"},
        ],
    },
    {
        "title": "Docker and Kubernetes: The Complete Guide",
        "provider": "Udemy",
        "resource_type": "COURSE",
        "url": "https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/",
        "description": "Containerization with Docker and orchestration with Kubernetes",
        "difficulty": "INTERMEDIATE",
        "estimated_hours": 45.0,
        "skill_mappings": [
            {"skill_name": SKILL_DOCKER, "relevance_score": 0.9, "coverage_type": "COMPREHENSIVE"},
            {"skill_name": SKILL_KUBERNETES, "relevance_score": 0.85, "coverage_type": "COMPREHENSIVE"},
        ],
    },
    {
        "title": "Machine Learning Specialization",
        "provider": "DeepLearning.AI (Coursera)",
        "resource_type": "COURSE",
        "url": "https://www.coursera.org/specializations/machine-learning-introduction",
        "description": "Foundational machine learning course by Andrew Ng",
        "difficulty": "INTERMEDIATE",
        "estimated_hours": 60.0,
        "skill_mappings": [
            {"skill_name": SKILL_MACHINE_LEARNING, "relevance_score": 0.95, "coverage_type": "COMPREHENSIVE"},
            {"skill_name": SKILL_PYTHON, "relevance_score": 0.7, "coverage_type": "PARTIAL"},
        ],
    },
    {
        "title": "Deep Learning Specialization",
        "provider": "DeepLearning.AI (Coursera)",
        "resource_type": "COURSE",
        "url": "https://www.coursera.org/specializations/deep-learning",
        "description": "Neural networks and deep learning",
        "difficulty": "ADVANCED",
        "estimated_hours": 70.0,
        "skill_mappings": [
            {"skill_name": SKILL_DEEP_LEARNING, "relevance_score": 0.95, "coverage_type": "COMPREHENSIVE"},
            {"skill_name": SKILL_TENSORFLOW, "relevance_score": 0.8, "coverage_type": "PARTIAL"},
            {"skill_name": SKILL_PYTORCH, "relevance_score": 0.8, "coverage_type": "PARTIAL"},
        ],
    },
    {
        "title": "Statistics and Probability",
        "provider": "Khan Academy",
        "resource_type": "COURSE",
        "url": "https://www.khanacademy.org/math/statistics-probability",
        "description": "Foundational statistics and probability",
        "difficulty": "BEGINNER",
        "estimated_hours": 50.0,
        "skill_mappings": [
            {"skill_name": SKILL_STATISTICS, "relevance_score": 0.95, "coverage_type": "COMPREHENSIVE"},
            {"skill_name": SKILL_PROBABILITY, "relevance_score": 0.9, "coverage_type": "COMPREHENSIVE"},
        ],
    },
    {
        "title": "Tableau Training",
        "provider": "Tableau",
        "resource_type": "TUTORIAL",
        "url": "https://www.tableau.com/learn/training",
        "description": "Official Tableau training tutorials",
        "difficulty": "BEGINNER",
        "estimated_hours": 20.0,
        "skill_mappings": [
            {"skill_name": SKILL_TABLEAU, "relevance_score": 0.95, "coverage_type": "COMPREHENSIVE"},
        ],
    },
    {
        "title": "Linux Administration",
        "provider": "Linux Foundation",
        "resource_type": "COURSE",
        "url": "https://training.linuxfoundation.org/",
        "description": "Linux system administration fundamentals",
        "difficulty": "INTERMEDIATE",
        "estimated_hours": 40.0,
        "skill_mappings": [
            {"skill_name": SKILL_LINUX, "relevance_score": 0.95, "coverage_type": "COMPREHENSIVE"},
        ],
    },
    {
        "title": "Prompt Engineering Guide",
        "provider": "OpenAI",
        "resource_type": "DOCUMENTATION",
        "url": "https://platform.openai.com/docs/guides/prompt-engineering",
        "description": "Best practices for LLM prompt engineering",
        "difficulty": "BEGINNER",
        "estimated_hours": 10.0,
        "skill_mappings": [
            {"skill_name": SKILL_PROMPT_ENGINEERING, "relevance_score": 0.95, "coverage_type": "COMPREHENSIVE"},
        ],
    },
    {
        "title": "Cybersecurity Fundamentals",
        "provider": "Microsoft",
        "resource_type": "COURSE",
        "url": "https://learn.microsoft.com/en-us/training/paths/sc-900/",
        "description": "Security, compliance, and identity fundamentals",
        "difficulty": "BEGINNER",
        "estimated_hours": 25.0,
        "skill_mappings": [
            {"skill_name": SKILL_NETWORK_SECURITY, "relevance_score": 0.85, "coverage_type": "COMPREHENSIVE"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Skill dependency definitions (prerequisite graph)
# Each entry: skill, prerequisite_skill, strength, source_reference
# ---------------------------------------------------------------------------

SKILL_DEPENDENCIES: list[dict[str, Any]] = [
    # Programming foundations
    {"skill": SKILL_JAVASCRIPT, "prerequisite_skill": SKILL_PYTHON, "strength": "SUPPORTING", "source_reference": "curated"},
    # Data science foundations
    {"skill": SKILL_PANDAS, "prerequisite_skill": SKILL_PYTHON, "strength": "REQUIRED", "source_reference": "curated"},
    {"skill": SKILL_NUMPY, "prerequisite_skill": SKILL_PYTHON, "strength": "REQUIRED", "source_reference": "curated"},
    {"skill": SKILL_SCIKIT_LEARN, "prerequisite_skill": SKILL_PANDAS, "strength": "REQUIRED", "source_reference": "curated"},
    {"skill": SKILL_SCIKIT_LEARN, "prerequisite_skill": SKILL_NUMPY, "strength": "REQUIRED", "source_reference": "curated"},
    {"skill": SKILL_MACHINE_LEARNING, "prerequisite_skill": SKILL_STATISTICS, "strength": "REQUIRED", "source_reference": "curated"},
    {"skill": SKILL_MACHINE_LEARNING, "prerequisite_skill": SKILL_PYTHON, "strength": "REQUIRED", "source_reference": "curated"},
    # Deep learning
    {"skill": SKILL_DEEP_LEARNING, "prerequisite_skill": SKILL_MACHINE_LEARNING, "strength": "REQUIRED", "source_reference": "curated"},
    {"skill": SKILL_TENSORFLOW, "prerequisite_skill": SKILL_DEEP_LEARNING, "strength": "SUPPORTING", "source_reference": "curated"},
    {"skill": SKILL_PYTORCH, "prerequisite_skill": SKILL_DEEP_LEARNING, "strength": "SUPPORTING", "source_reference": "curated"},
    # AI Engineering
    {"skill": SKILL_RAG, "prerequisite_skill": SKILL_PYTHON, "strength": "REQUIRED", "source_reference": "curated"},
    {"skill": SKILL_PROMPT_ENGINEERING, "prerequisite_skill": SKILL_PYTHON, "strength": "SUPPORTING", "source_reference": "curated"},
    # Cloud/DevOps
    {"skill": SKILL_KUBERNETES, "prerequisite_skill": SKILL_DOCKER, "strength": "REQUIRED", "source_reference": "curated"},
    {"skill": SKILL_AWS, "prerequisite_skill": SKILL_LINUX, "strength": "SUPPORTING", "source_reference": "curated"},
    # Data analysis
    {"skill": SKILL_TABLEAU, "prerequisite_skill": SKILL_SQL, "strength": "SUPPORTING", "source_reference": "curated"},
    {"skill": SKILL_POWER_BI, "prerequisite_skill": SKILL_EXCEL, "strength": "SUPPORTING", "source_reference": "curated"},
    # Cybersecurity
    {"skill": SKILL_NETWORK_SECURITY, "prerequisite_skill": SKILL_LINUX, "strength": "REQUIRED", "source_reference": "curated"},
]

# ---------------------------------------------------------------------------
# Interview question bank definitions
# Each question: id, career_id (nullable), question_text, question_type,
# difficulty, source, expected_competency, skill_mappings
# ---------------------------------------------------------------------------

INTERVIEW_QUESTIONS: list[dict[str, Any]] = [
    {
        "question_text": "Explain the difference between == and === in JavaScript.",
        "question_type": "TECHNICAL",
        "difficulty": "EASY",
        "source": "CURATED",
        "expected_competency": "Understands JavaScript equality operators",
        "skill_mappings": [
            {"skill_name": SKILL_JAVASCRIPT, "relevance_score": 0.9},
        ],
    },
    {
        "question_text": "What is a SQL JOIN and when would you use a LEFT JOIN vs INNER JOIN?",
        "question_type": "TECHNICAL",
        "difficulty": "EASY",
        "source": "CURATED",
        "expected_competency": "Understands SQL join types",
        "skill_mappings": [
            {"skill_name": SKILL_SQL, "relevance_score": 0.9},
        ],
    },
    {
        "question_text": "Describe the difference between supervised and unsupervised machine learning.",
        "question_type": "CONCEPTUAL",
        "difficulty": "MEDIUM",
        "source": "CURATED",
        "expected_competency": "Understands ML paradigm categories",
        "skill_mappings": [
            {"skill_name": SKILL_MACHINE_LEARNING, "relevance_score": 0.9},
        ],
    },
    {
        "question_text": "How would you handle missing data in a pandas DataFrame?",
        "question_type": "TECHNICAL",
        "difficulty": "EASY",
        "source": "CURATED",
        "expected_competency": "Knows pandas data cleaning methods",
        "skill_mappings": [
            {"skill_name": SKILL_PANDAS, "relevance_score": 0.85},
            {"skill_name": SKILL_PYTHON, "relevance_score": 0.6},
        ],
    },
    {
        "question_text": "What is the purpose of a Dockerfile and how does it differ from docker-compose?",
        "question_type": "TECHNICAL",
        "difficulty": "MEDIUM",
        "source": "CURATED",
        "expected_competency": "Understands containerization concepts",
        "skill_mappings": [
            {"skill_name": SKILL_DOCKER, "relevance_score": 0.9},
        ],
    },
    {
        "question_text": "Explain the CAP theorem in distributed systems.",
        "question_type": "CONCEPTUAL",
        "difficulty": "HARD",
        "source": "CURATED",
        "expected_competency": "Understands distributed system trade-offs",
        "skill_mappings": [
            {"skill_name": SKILL_AWS, "relevance_score": 0.6},
            {"skill_name": SKILL_POSTGRESQL, "relevance_score": 0.7},
        ],
    },
    {
        "question_text": "How would you design a REST API endpoint for user authentication?",
        "question_type": "SCENARIO",
        "difficulty": "MEDIUM",
        "source": "CURATED",
        "expected_competency": "Can design secure API endpoints",
        "skill_mappings": [
            {"skill_name": SKILL_REST_API, "relevance_score": 0.9},
            {"skill_name": SKILL_PYTHON, "relevance_score": 0.5},
        ],
    },
    {
        "question_text": "What is prompt engineering and why does it matter for LLM applications?",
        "question_type": "CONCEPTUAL",
        "difficulty": "EASY",
        "source": "CURATED",
        "expected_competency": "Understands LLM prompting fundamentals",
        "skill_mappings": [
            {"skill_name": SKILL_PROMPT_ENGINEERING, "relevance_score": 0.95},
        ],
    },
    {
        "question_text": "Describe how RAG (Retrieval-Augmented Generation) works.",
        "question_type": "CONCEPTUAL",
        "difficulty": "MEDIUM",
        "source": "CURATED",
        "expected_competency": "Understands RAG architecture",
        "skill_mappings": [
            {"skill_name": SKILL_RAG, "relevance_score": 0.9},
            {"skill_name": SKILL_PYTHON, "relevance_score": 0.4},
        ],
    },
    {
        "question_text": "What are the main differences between TensorFlow and PyTorch?",
        "question_type": "TECHNICAL",
        "difficulty": "MEDIUM",
        "source": "CURATED",
        "expected_competency": "Compares ML frameworks",
        "skill_mappings": [
            {"skill_name": SKILL_TENSORFLOW, "relevance_score": 0.8},
            {"skill_name": SKILL_PYTORCH, "relevance_score": 0.8},
        ],
    },
    {
        "question_text": "How would you secure a Linux server exposed to the internet?",
        "question_type": "TECHNICAL",
        "difficulty": "MEDIUM",
        "source": "CURATED",
        "expected_competency": "Knows Linux security hardening",
        "skill_mappings": [
            {"skill_name": SKILL_LINUX, "relevance_score": 0.9},
        ],
    },
    {
        "question_text": "What is Kubernetes and how does it manage container orchestration?",
        "question_type": "TECHNICAL",
        "difficulty": "MEDIUM",
        "source": "CURATED",
        "expected_competency": "Understands Kubernetes concepts",
        "skill_mappings": [
            {"skill_name": SKILL_KUBERNETES, "relevance_score": 0.9},
        ],
    },
    {
        "question_text": "Explain A/B testing and how you would determine statistical significance.",
        "question_type": "CONCEPTUAL",
        "difficulty": "MEDIUM",
        "source": "CURATED",
        "expected_competency": "Understands experimental design",
        "skill_mappings": [
            {"skill_name": SKILL_STATISTICS, "relevance_score": 0.9},
        ],
    },
    {
        "question_text": "How would you create an interactive dashboard in Tableau?",
        "question_type": "TECHNICAL",
        "difficulty": "EASY",
        "source": "CURATED",
        "expected_competency": "Knows Tableau dashboard creation",
        "skill_mappings": [
            {"skill_name": SKILL_TABLEAU, "relevance_score": 0.9},
        ],
    },
]

__all__ = [
    "CAREERS",
    "LEARNING_RESOURCES",
    "SKILL_DEPENDENCIES",
    "INTERVIEW_QUESTIONS",
]
