"""
Database Seeding Script for Wiring Diagram QC Assistant.
Seeds initial demo tenant (Spandsons Horizon), admin, engineer, demo project, and standards.
"""

import asyncio
import uuid
from sqlalchemy import select
from .database import AsyncSessionLocal, init_db
from .models import Organization, Project, User
from ..core.security import hash_password



async def seed_data():
    """Idempotently seed demonstration data into database."""
    await init_db()

    async with AsyncSessionLocal() as session:
        # 1. Check or Create Demo Organization
        org_slug = "spandsons-horizon"
        stmt = select(Organization).where(Organization.slug == org_slug)
        existing_org = (await session.execute(stmt)).scalar_one_or_none()

        if not existing_org:
            org_id = str(uuid.uuid4())
            org = Organization(
                id=org_id,
                name="Spandsons Horizon Engineering Pvt. Ltd.",
                slug=org_slug,
                plan_tier="ENTERPRISE",
                credits_remaining=250,
            )
            session.add(org)
            await session.commit()
            print(f"[Seed] Created Organization: {org.name} ({org.id})")
        else:
            org = existing_org
            print(f"[Seed] Organization already exists: {org.name}")

        # 2. Check or Create Demo Users
        users_to_seed = [
            ("pravin@spandsons.com", "Pravin", "ADMIN", "Pravin@12345"),
            ("gogulnath@spandsons.com", "Gogulnath", "ENGINEER", "Gogulnath@12345"),
            ("inspector@spandsons.com", "Lead QC Inspector", "REVIEWER", "Inspector@12345"),
        ]

        for email, full_name, role, password in users_to_seed:
            user_stmt = select(User).where(User.email == email)
            existing_user = (await session.execute(user_stmt)).scalar_one_or_none()

            if not existing_user:
                user = User(
                    id=str(uuid.uuid4()),
                    organization_id=org.id,
                    email=email,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    role=role,
                    is_active=True,
                )
                session.add(user)
                print(f"[Seed] Created User: {email} ({role})")
            else:
                print(f"[Seed] User already exists: {email}")

        await session.commit()

        # 3. Check or Create Demo Project
        proj_stmt = (
            select(Project)
            .where(Project.organization_id == org.id)
            .where(Project.name == "Commercial Avionics Harness WD-777")
        )
        existing_proj = (await session.execute(proj_stmt)).scalar_one_or_none()

        if not existing_proj:
            project = Project(
                id=str(uuid.uuid4()),
                organization_id=org.id,
                name="Commercial Avionics Harness WD-777",
                description="Boeing 777X avionics wiring schematics and harness routing manuals.",
            )
            session.add(project)
            await session.commit()
            print(f"[Seed] Created Project: {project.name}")
        else:
            print(f"[Seed] Project already exists: {existing_proj.name}")

    print("[Seed] Seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(seed_data())
