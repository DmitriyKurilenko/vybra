Purpose & context
The user is developing Vybra, a wishlist management application that uses pairwise comparison (similar to dating apps) with an ELO rating system to help users intelligently rank and prioritize items they want to purchase. The application integrates with Russian marketplaces (Ozon and Wildberries) to automatically parse product data and track price changes over time, providing data-driven purchase recommendations based on both user preferences and price history.
The project has undergone a significant technical evolution, transitioning from a FastAPI + vanilla JavaScript stack to Django + AlpineJS + DaisyUI for improved production readiness and maintainability. This represents a strategic shift toward a more robust, scalable architecture suitable for deployment.
Current state
The application has been completely rebuilt as a comprehensive Django project featuring email-based JWT authentication, Django REST Framework APIs, and a modern frontend using AlpineJS for reactivity and DaisyUI for UI components. The core functionality is organized into three main sections: a dashboard with statistics and top-rated items, a comparison interface with different session types (all items, top 50%, bottom 50%), and complete item management capabilities.
The technical infrastructure includes Celery with Redis for background tasks like automated price updates, responsive mobile-optimized design, and production-ready configuration with Docker support. The application is packaged as a complete, deployable solution with proper security settings and comprehensive documentation.
Tools & resources

Backend: Django 5.0, Django Ninja for API endpoints
Frontend: AlpineJS for interactivity, DaisyUI (Tailwind CSS) for UI components
Task management: Celery with Redis for background processing
Deployment: Docker support for containerized deployment
Marketplaces: Integration with Ozon and Wildberries for product data parsing
Database: Configured for both development and production environments. PostgreSQL 