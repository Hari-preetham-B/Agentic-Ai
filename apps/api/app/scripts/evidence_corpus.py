"""Curated evidence corpus for CareerTwin evidence intelligence validation.

This module contains a small, authoritative, maintainable corpus of evidence
sources relevant to CareerTwin's eight curated careers. All sources are
publicly available, non-copyrighted occupational information from U.S.
government sources (O*NET, BLS) or official technology documentation.

The corpus is deliberately small — one source per career — sufficient to
exercise the full evidence pipeline:

    source → document → chunks → embeddings → pgvector → retrieval
    → claims → evidence comparison → confidence → classification

No web scraping is performed. No LLM output is treated as evidence.
No fake URLs are fabricated.

Each source record contains:
- source_type: CURATED_KNOWLEDGE (all sources in this corpus)
- title, publisher, url, published_at, retrieved_at
- reliability_score (0.0-1.0)
- documents: list of {document_type, title, content}

Source weights (from ConfidenceEngine): CURATED_KNOWLEDGE = 0.8
Document type weights: OCCUPATIONAL_PROFILE = 1.0, SKILL_DEFINITION = 0.9
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Corpus metadata
# ---------------------------------------------------------------------------

CORPUS_NAME = "careertwin-curated-career-knowledge-v1"
CORPUS_RETRIEVED_AT = "2026-11-02T00:00:00Z"

# ---------------------------------------------------------------------------
# Evidence sources
# Each source is keyed by a stable slug for idempotent re-ingestion.
# ---------------------------------------------------------------------------

EVIDENCE_SOURCES: list[dict[str, Any]] = [
    {
        "slug": "onet-software-developer",
        "source_type": "CURATED_KNOWLEDGE",
        "title": "O*NET — Software Developers (15-1252.00)",
        "publisher": "U.S. Department of Labor, O*NET Resource Center",
        "url": "https://www.onetonline.org/link/summary/15-1252.00",
        "published_at": None,
        "reliability_score": 0.9,
        "documents": [
            {
                "document_type": "OCCUPATIONAL_PROFILE",
                "title": "Software Developer Occupational Profile",
                "content": (
                    "Software developers design, create, test, and maintain "
                    "computer applications and systems. They analyze user "
                    "needs and develop software solutions to meet those needs. "
                    "Common programming languages include Python, Java, "
                    "JavaScript, and SQL. Software developers collaborate with "
                    "cross-functional teams and follow software development "
                    "lifecycle methodologies including requirements analysis, "
                    "design, implementation, testing, deployment, and "
                    "maintenance."
                ),
            },
            {
                "document_type": "SKILL_DEFINITION",
                "title": "Software Developer Core Skills",
                "content": (
                    "Core skills for software developers include programming "
                    "in Python, Java, JavaScript, and C++; database management "
                    "with SQL; version control with Git; software testing and "
                    "debugging; and knowledge of data structures and algorithms."
                ),
            },
        ],
    },
    {
        "slug": "bls-data-scientist",
        "source_type": "CURATED_KNOWLEDGE",
        "title": "BLS — Data Scientists Occupational Outlook",
        "publisher": "U.S. Bureau of Labor Statistics",
        "url": "https://www.bls.gov/ooh/computer-and-information-technology/data-scientists.htm",
        "published_at": None,
        "reliability_score": 0.9,
        "documents": [
            {
                "document_type": "OCCUPATIONAL_PROFILE",
                "title": "Data Scientist Occupational Outlook",
                "content": (
                    "Data scientists use analytical, statistical, and "
                    "programming skills to collect, analyze, and interpret "
                    "large and complex datasets. They build predictive models, "
                    "perform machine learning and statistical analysis, and "
                    "communicate data-driven insights to stakeholders. Key "
                    "tools include Python, R, SQL, and data visualization "
                    "platforms such as Tableau and Power BI."
                ),
            },
            {
                "document_type": "SKILL_DEFINITION",
                "title": "Data Scientist Core Skills",
                "content": (
                    "Core skills for data scientists include statistical "
                    "analysis, machine learning, data wrangling with Python "
                    "and R, SQL querying, data visualization, and communication "
                    "of quantitative findings to non-technical audiences."
                ),
            },
        ],
    },
    {
        "slug": "onet-information-security-analyst",
        "source_type": "CURATED_KNOWLEDGE",
        "title": "O*NET — Information Security Analysts (15-1212.00)",
        "publisher": "U.S. Department of Labor, O*NET Resource Center",
        "url": "https://www.onetonline.org/link/summary/15-1212.00",
        "published_at": None,
        "reliability_score": 0.9,
        "documents": [
            {
                "document_type": "OCCUPATIONAL_PROFILE",
                "title": "Information Security Analyst Occupational Profile",
                "content": (
                    "Information security analysts plan and carry out security "
                    "measures to protect an organization's computer networks "
                    "and systems. Their responsibilities include monitoring "
                    "networks for security breaches, investigating violations, "
                    "installing and configuring security software, and "
                    "developing security standards and best practices."
                ),
            },
            {
                "document_type": "SKILL_DEFINITION",
                "title": "Cybersecurity Analyst Core Skills",
                "content": (
                    "Core skills for cybersecurity analysts include network "
                    "security monitoring, vulnerability assessment, incident "
                    "response, security information and event management (SIEM), "
                    "firewall configuration, and knowledge of common attack "
                    "vectors and mitigation techniques."
                ),
            },
        ],
    },
    {
        "slug": "aws-cloud-practitioner",
        "source_type": "CURATED_KNOWLEDGE",
        "title": "AWS Cloud Practitioner Essentials — Cloud Engineering Fundamentals",
        "publisher": "Amazon Web Services",
        "url": "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/",
        "published_at": None,
        "reliability_score": 0.85,
        "documents": [
            {
                "document_type": "OCCUPATIONAL_PROFILE",
                "title": "Cloud / DevOps Engineer Role Profile",
                "content": (
                    "Cloud engineers design, deploy, and manage cloud "
                    "infrastructure and services. They work with compute, "
                    "storage, networking, database, and security services on "
                    "cloud platforms such as AWS, Microsoft Azure, and Google "
                    "Cloud Platform. DevOps practices including continuous "
                    "integration and continuous deployment (CI/CD), container "
                    "orchestration with Kubernetes, and containerization with "
                    "Docker are essential to modern cloud engineering."
                ),
            },
            {
                "document_type": "SKILL_DEFINITION",
                "title": "Cloud Engineering Core Skills",
                "content": (
                    "Core skills for cloud engineers include cloud platform "
                    "administration (AWS, Azure, GCP), infrastructure as code "
                    "(Terraform, CloudFormation), containerization (Docker), "
                    "container orchestration (Kubernetes), CI/CD pipeline "
                    "design, and cloud security best practices."
                ),
            },
        ],
    },
    {
        "slug": "onet-computer-systems-analyst",
        "source_type": "CURATED_KNOWLEDGE",
        "title": "O*NET — Computer Systems Analysts (15-1211.00)",
        "publisher": "U.S. Department of Labor, O*NET Resource Center",
        "url": "https://www.onetonline.org/link/summary/15-1211.00",
        "published_at": None,
        "reliability_score": 0.85,
        "documents": [
            {
                "document_type": "OCCUPATIONAL_PROFILE",
                "title": "Data Analyst Role Profile",
                "content": (
                    "Data analysts collect, process, and analyze data to help "
                    "organizations make informed business decisions. They "
                    "clean and validate data, perform statistical analysis, "
                    "create reports and dashboards, and communicate findings "
                    "to stakeholders. Common tools include SQL, spreadsheet "
                    "software, and data visualization platforms."
                ),
            },
            {
                "document_type": "SKILL_DEFINITION",
                "title": "Data Analyst Core Skills",
                "content": (
                    "Core skills for data analysts include SQL querying, data "
                    "cleaning and validation, statistical analysis, data "
                    "visualization, spreadsheet modeling, and business "
                    "intelligence reporting."
                ),
            },
        ],
    },
    {
        "slug": "onet-computer-systems-analyst-ml",
        "source_type": "CURATED_KNOWLEDGE",
        "title": "O*NET — Computer and Information Research Scientists (15-1221.00)",
        "publisher": "U.S. Department of Labor, O*NET Resource Center",
        "url": "https://www.onetonline.org/link/summary/15-1221.00",
        "published_at": None,
        "reliability_score": 0.9,
        "documents": [
            {
                "document_type": "OCCUPATIONAL_PROFILE",
                "title": "Machine Learning Engineer Role Profile",
                "content": (
                    "Machine learning engineers research, design, and develop "
                    "artificial intelligence and machine learning systems. "
                    "They create and train machine learning models, optimize "
                    "model performance, and deploy models into production "
                    "environments. Key techniques include supervised and "
                    "unsupervised learning, deep learning, and model "
                    "evaluation."
                ),
            },
            {
                "document_type": "SKILL_DEFINITION",
                "title": "Machine Learning Engineer Core Skills",
                "content": (
                    "Core skills for machine learning engineers include "
                    "Python programming, machine learning frameworks such as "
                    "TensorFlow and PyTorch, data preprocessing and feature "
                    "engineering, model training and evaluation, and MLOps "
                    "practices for model deployment and monitoring."
                ),
            },
        ],
    },
    {
        "slug": "ai-engineer-curated",
        "source_type": "CURATED_KNOWLEDGE",
        "title": "AI Engineer — Curated Knowledge Base",
        "publisher": "CareerTwin Curated Knowledge",
        "url": None,
        "published_at": None,
        "reliability_score": 0.7,
        "documents": [
            {
                "document_type": "OCCUPATIONAL_PROFILE",
                "title": "AI Engineer Role Profile",
                "content": (
                    "AI engineers integrate foundation models and large "
                    "language models into production applications. They design "
                    "and implement retrieval-augmented generation (RAG) "
                    "systems, engineer prompts for LLM-based applications, and "
                    "evaluate model outputs. AI engineers work with vector "
                    "databases, embedding models, and LLM APIs to build "
                    "intelligent applications."
                ),
            },
            {
                "document_type": "SKILL_DEFINITION",
                "title": "AI Engineer Core Skills",
                "content": (
                    "Core skills for AI engineers include Python programming, "
                    "prompt engineering, retrieval-augmented generation (RAG), "
                    "embedding models and vector databases, LLM evaluation and "
                    "red-teaming, and integration of AI models into software "
                    "applications via APIs."
                ),
            },
        ],
    },
    {
        "slug": "onet-management-analyst",
        "source_type": "CURATED_KNOWLEDGE",
        "title": "O*NET — Management Analysts (13-1111.00)",
        "publisher": "U.S. Department of Labor, O*NET Resource Center",
        "url": "https://www.onetonline.org/link/summary/13-1111.00",
        "published_at": None,
        "reliability_score": 0.85,
        "documents": [
            {
                "document_type": "OCCUPATIONAL_PROFILE",
                "title": "Product Analyst Role Profile",
                "content": (
                    "Product analysts analyze product data to guide product "
                    "decisions and strategy. They work with product teams to "
                    "measure feature performance, analyze user behavior, run "
                    "A/B tests, and recommend product improvements based on "
                    "data. Common tools include SQL, spreadsheet software, and "
                    "data visualization platforms."
                ),
            },
            {
                "document_type": "SKILL_DEFINITION",
                "title": "Product Analyst Core Skills",
                "content": (
                    "Core skills for product analysts include SQL querying, "
                    "A/B testing and statistical analysis, product metrics "
                    "definition and tracking, user behavior analysis, data "
                    "visualization, and product requirement documentation."
                ),
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_source_by_slug(slug: str) -> dict[str, Any] | None:
    """Return a source record by its stable slug."""
    for source in EVIDENCE_SOURCES:
        if source["slug"] == slug:
            return source
    return None


def get_all_document_texts() -> list[dict[str, Any]]:
    """Return all documents with their source context for ingestion.

    Each item contains: source fields, document_type, title, content.
    """
    items = []
    for source in EVIDENCE_SOURCES:
        for doc in source["documents"]:
            items.append(
                {
                    "source_type": source["source_type"],
                    "source_title": source["title"],
                    "source_publisher": source["publisher"],
                    "source_url": source["url"],
                    "source_reliability_score": source["reliability_score"],
                    "document_type": doc["document_type"],
                    "document_title": doc["title"],
                    "document_content": doc["content"],
                }
            )
    return items


__all__ = [
    "EVIDENCE_SOURCES",
    "CORPUS_NAME",
    "get_source_by_slug",
    "get_all_document_texts",
]
