import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.passwords import hash_password
from app.models import (
    College,
    Request,
    Resource,
    Transfer,
    TransferStatusHistory,
    User,
)

logger = logging.getLogger(__name__)

SHARED_DEMO_PASSWORD = "CampusCycleDemo2026!"
MANIFEST_PATH = Path("/data/demo_seed_manifest.json") if Path("/data").is_dir() else Path("data/demo_seed_manifest.json")
AISHE_SOURCE_PATH = Path("data/aishe_verified_institutions.json")


def _utc(hours_ago: int = 0, days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)


def seed_demo_data(db: Session, *, manifest_path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Seed idempotent, realistic demonstration data derived from verified AISHE institutions."""
    manifest_records: dict[str, list[dict[str, Any]]] = {
        "colleges": [],
        "users": [],
        "resources": [],
        "requests": [],
        "transfers": [],
        "transfer_history": [],
    }

    print("Beginning CampusCycle demonstration data seeding...")

    # -------------------------------------------------------------------------
    # 1. Colleges (Verified AISHE Higher Education Institutions in Chennai, TN)
    # -------------------------------------------------------------------------
    college_definitions = [
        {
            "name": "Anna University",
            "address": "Sardar Patel Road, Guindy",
            "city": "Chennai",
            "contact_email": "registrar@annauniv.edu",
            "verification_status": "verified",
        },
        {
            "name": "Indian Institute of Technology Madras",
            "address": "Sardar Patel Road, IIT P.O.",
            "city": "Chennai",
            "contact_email": "registrar@iitm.ac.in",
            "verification_status": "verified",
        },
        {
            "name": "University of Madras",
            "address": "Centenary Buildings, Kamarajar Salai, Chepauk",
            "city": "Chennai",
            "contact_email": "registrar@unom.ac.in",
            "verification_status": "verified",
        },
        {
            "name": "Loyola College",
            "address": "Sterling Road, Nungambakkam",
            "city": "Chennai",
            "contact_email": "principal@loyolacollege.edu",
            "verification_status": "verified",
        },
        {
            "name": "Madras Christian College",
            "address": "Velachery Main Road, East Tambaram",
            "city": "Chennai",
            "contact_email": "principal@mcc.edu.in",
            "verification_status": "pending",  # Demonstrates college approval workflow
        },
    ]

    colleges_by_name: dict[str, College] = {}
    for c_def in college_definitions:
        existing = db.scalar(select(College).where(College.name == c_def["name"]))
        if existing is None:
            created = College(
                name=c_def["name"],
                address=c_def["address"],
                city=c_def["city"],
                contact_email=c_def["contact_email"],
                verification_status=c_def["verification_status"],
                created_at=_utc(days_ago=30),
                updated_at=_utc(days_ago=10),
            )
            db.add(created)
            db.flush()
            colleges_by_name[c_def["name"]] = created
            manifest_records["colleges"].append({"id": created.id, "name": created.name})
            print(f"  + College created: {created.name} (ID {created.id})")
        else:
            colleges_by_name[c_def["name"]] = existing
            manifest_records["colleges"].append({"id": existing.id, "name": existing.name})
            print(f"  = College exists: {existing.name} (ID {existing.id})")

    # -------------------------------------------------------------------------
    # 2. Demonstration Users (Fictional student & representative identities)
    # -------------------------------------------------------------------------
    hashed_pwd = hash_password(SHARED_DEMO_PASSWORD)

    user_definitions = [
        # Platform Admin (College ID: None)
        {
            "name": "CampusCycle Platform Administrator",
            "email": "admin@example.edu",
            "role": "platform_admin",
            "college": None,
        },
        # Anna University Representatives & Faculty
        {
            "name": "Dr. K. Ramasamy",
            "email": "rep.anna@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["Anna University"],
        },
        {
            "name": "Priya Sundaram",
            "email": "priya.sundaram@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["Anna University"],
        },
        # IIT Madras Representatives & Faculty
        {
            "name": "Prof. M. Sridharan",
            "email": "rep.iitm@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["Indian Institute of Technology Madras"],
        },
        {
            "name": "Anand Venkatesh",
            "email": "anand.venkatesh@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["Indian Institute of Technology Madras"],
        },
        # University of Madras Representatives & Faculty
        {
            "name": "Dr. S. Meenakshi",
            "email": "rep.unom@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["University of Madras"],
        },
        {
            "name": "Karthik Balaji",
            "email": "karthik.balaji@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["University of Madras"],
        },
        # Loyola College Representatives & Faculty
        {
            "name": "Rev. Dr. A. Thomas",
            "email": "rep.loyola@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["Loyola College"],
        },
        {
            "name": "Deepa Natarajan",
            "email": "deepa.natarajan@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["Loyola College"],
        },
        {
            "name": "Rajesh Kannan",
            "email": "rajesh.kannan@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["Loyola College"],
        },
        # Madras Christian College Representative (Pending college)
        {
            "name": "Dr. Paul Wilson",
            "email": "rep.mcc@example.edu",
            "role": "college_representative",
            "college": colleges_by_name["Madras Christian College"],
        },
    ]

    users_by_email: dict[str, User] = {}
    for u_def in user_definitions:
        existing = db.scalar(select(User).where(User.email == u_def["email"]))
        if existing is None:
            created = User(
                name=u_def["name"],
                email=u_def["email"],
                password_hash=hashed_pwd,
                role=u_def["role"],
                college=u_def["college"],
                is_active=True,
                created_at=_utc(days_ago=25),
                updated_at=_utc(days_ago=5),
            )
            db.add(created)
            db.flush()
            users_by_email[u_def["email"]] = created
            manifest_records["users"].append({"id": created.id, "email": created.email, "role": created.role})
            print(f"  + User created: {created.email} [{created.role}] (ID {created.id})")
        else:
            users_by_email[u_def["email"]] = existing
            manifest_records["users"].append({"id": existing.id, "email": existing.email, "role": existing.role})
            print(f"  = User exists: {existing.email} (ID {existing.id})")

    # -------------------------------------------------------------------------
    # 3. Resource Listings (Realistic academic equipment & textbook inventory)
    # -------------------------------------------------------------------------
    resource_definitions = [
        # Anna University Listings
        {
            "key": "anna_clrs",
            "college": colleges_by_name["Anna University"],
            "creator": users_by_email["rep.anna@example.edu"],
            "name": "Introduction to Algorithms (CLRS) 4th Edition",
            "description": "Standard computer science reference textbook. Excellent condition, unmarked pages.",
            "category": "Books",
            "condition": "Like new",
            "quantity_total": 15,
            "quantity_available": 10,
            "quantity_reserved": 5,  # Reserved for approved requests
            "unit": "copies",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "anna_oscilloscope",
            "college": colleges_by_name["Anna University"],
            "creator": users_by_email["priya.sundaram@example.edu"],
            "name": "Digital Storage Oscilloscope 100MHz (Rigol DS1054Z)",
            "description": "4-channel 100MHz bandwidth digital oscilloscope with probes and calibration certificates.",
            "category": "Lab equipment",
            "condition": "Good",
            "quantity_total": 4,
            "quantity_available": 4,
            "quantity_reserved": 0,
            "unit": "units",
            "transfer_type": "exchange",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "anna_calculators",
            "college": colleges_by_name["Anna University"],
            "creator": users_by_email["rep.anna@example.edu"],
            "name": "Texas Instruments TI-84 Plus CE Graphing Calculators",
            "description": "High-resolution color backlit display graphing calculators for engineering mathematics and statistics.",
            "category": "Electronics",
            "condition": "Like new",
            "quantity_total": 10,
            "quantity_available": 6,
            "quantity_reserved": 4,  # Partial donation approval
            "unit": "units",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "anna_stm32",
            "college": colleges_by_name["Anna University"],
            "creator": users_by_email["priya.sundaram@example.edu"],
            "name": "Microcontroller Development Kits (STM32 Nucleo-64)",
            "description": "ARM Cortex-M4 development boards with integrated ST-LINK debugger for embedded systems projects.",
            "category": "Electronics",
            "condition": "New",
            "quantity_total": 20,
            "quantity_available": 20,
            "quantity_reserved": 0,
            "unit": "kits",
            "transfer_type": "sale",
            "indicative_price": 1200.00,
            "status": "active",
        },
        {
            "key": "anna_fluid_mech",
            "college": colleges_by_name["Anna University"],
            "creator": users_by_email["rep.anna@example.edu"],
            "name": "Fluid Mechanics & Hydraulic Machinery Reference Collection",
            "description": "Collection of 8 standard reference sets by Modi & Seth and Bansal for mechanical/civil engineering labs.",
            "category": "Study material",
            "condition": "Good",
            "quantity_total": 8,
            "quantity_available": 8,
            "quantity_reserved": 0,
            "unit": "sets",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        # IIT Madras Listings
        {
            "key": "iitm_rpi",
            "college": colleges_by_name["Indian Institute of Technology Madras"],
            "creator": users_by_email["rep.iitm@example.edu"],
            "name": "Raspberry Pi 4 Model B (4GB RAM) Lab Bundles",
            "description": "Quad-core single board computers with official power supply, micro-HDMI cables, and 32GB SD cards.",
            "category": "Electronics",
            "condition": "Like new",
            "quantity_total": 12,
            "quantity_available": 8,
            "quantity_reserved": 4,  # Reserved for exchange request
            "unit": "kits",
            "transfer_type": "exchange",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "iitm_prml",
            "college": colleges_by_name["Indian Institute of Technology Madras"],
            "creator": users_by_email["anand.venkatesh@example.edu"],
            "name": "Pattern Recognition and Machine Learning (Bishop)",
            "description": "Hardcover classic textbook for graduate AI/ML courses. Hard bound and clean.",
            "category": "Books",
            "condition": "Good",
            "quantity_total": 6,  # 10 original minus 4 completed delivery
            "quantity_available": 6,
            "quantity_reserved": 0,
            "unit": "copies",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "iitm_microscopes",
            "college": colleges_by_name["Indian Institute of Technology Madras"],
            "creator": users_by_email["rep.iitm@example.edu"],
            "name": "Optical Microscopes with LED Illumination (Binocular)",
            "description": "Precision binocular biological microscopes 40X-1000X with oil immersion objectives.",
            "category": "Lab equipment",
            "condition": "Like new",
            "quantity_total": 6,
            "quantity_available": 6,
            "quantity_reserved": 0,
            "unit": "units",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "iitm_fpga",
            "college": colleges_by_name["Indian Institute of Technology Madras"],
            "creator": users_by_email["anand.venkatesh@example.edu"],
            "name": "FPGA Development Boards (Xilinx Spartan-7)",
            "description": "High-density FPGA development boards for digital logic and VLSI laboratory experiments.",
            "category": "Electronics",
            "condition": "Like new",
            "quantity_total": 5,
            "quantity_available": 3,
            "quantity_reserved": 2,  # Confirmed purchase enquiry
            "unit": "boards",
            "transfer_type": "sale",
            "indicative_price": 4500.00,
            "status": "active",
        },
        {
            "key": "iitm_calipers",
            "college": colleges_by_name["Indian Institute of Technology Madras"],
            "creator": users_by_email["rep.iitm@example.edu"],
            "name": "Mechanical Workshop Precision Calipers & Micrometers",
            "description": "Vernier calipers (0-150mm, 0.02mm accuracy) and screw gauges in fitted hardwood storage cases.",
            "category": "Lab equipment",
            "condition": "Good",
            "quantity_total": 15,
            "quantity_available": 10,
            "quantity_reserved": 5,  # In disputed transfer leg
            "unit": "sets",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        # University of Madras Listings
        {
            "key": "unom_clayden",
            "college": colleges_by_name["University of Madras"],
            "creator": users_by_email["rep.unom@example.edu"],
            "name": "Organic Chemistry (Clayden, Greeves, Warren) 2nd Edition",
            "description": "Comprehensive reference volumes for organic synthesis and reaction mechanisms.",
            "category": "Books",
            "condition": "Good",
            "quantity_total": 8,  # 12 original minus 4 completed delivery
            "quantity_available": 8,
            "quantity_reserved": 0,
            "unit": "copies",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "unom_cuvettes",
            "college": colleges_by_name["University of Madras"],
            "creator": users_by_email["karthik.balaji@example.edu"],
            "name": "Spectrophotometer Cuvettes & Calibration Standards",
            "description": "Precision optical quartz glass cuvettes (10mm path length) with PTFE stoppers in protective boxes.",
            "category": "Lab equipment",
            "condition": "New",
            "quantity_total": 25,
            "quantity_available": 23,
            "quantity_reserved": 2,  # Reserved for approved request
            "unit": "boxes",
            "transfer_type": "sale",
            "indicative_price": 650.00,
            "status": "active",
        },
        {
            "key": "unom_dsa_notes",
            "college": colleges_by_name["University of Madras"],
            "creator": users_by_email["rep.unom@example.edu"],
            "name": "Advanced Data Structures & Algorithms Problem Sets",
            "description": "Curated departmental tutorial booklets, complexity analysis guides, and annotated solution keys.",
            "category": "Study material",
            "condition": "Like new",
            "quantity_total": 30,
            "quantity_available": 30,
            "quantity_reserved": 0,  # Cancelled request released stock
            "unit": "booklets",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "unom_arduino",
            "college": colleges_by_name["University of Madras"],
            "creator": users_by_email["karthik.balaji@example.edu"],
            "name": "Arduino Starter Component Sets with Sensors & Breadboards",
            "description": "Microcontroller learning kits with ultrasonic sensors, LCD displays, stepper motors and jumper wires.",
            "category": "Electronics",
            "condition": "Like new",
            "quantity_total": 18,
            "quantity_available": 14,
            "quantity_reserved": 4,  # Reserved as offered resource in exchange
            "unit": "kits",
            "transfer_type": "exchange",
            "indicative_price": None,
            "status": "active",
        },
        # Loyola College Listings
        {
            "key": "loyola_slides",
            "college": colleges_by_name["Loyola College"],
            "creator": users_by_email["rep.loyola@example.edu"],
            "name": "General Biology Prepared Microscope Slides Set",
            "description": "Botanical and zoological tissue cross-section specimens mounted on optical glass slides.",
            "category": "Lab equipment",
            "condition": "Like new",
            "quantity_total": 8,
            "quantity_available": 6,
            "quantity_reserved": 2,  # In-transit transfer
            "unit": "sets",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "loyola_stats",
            "college": colleges_by_name["Loyola College"],
            "creator": users_by_email["deepa.natarajan@example.edu"],
            "name": "Statistics for Business and Economics (Anderson, Sweeney)",
            "description": "Prescribed textbook for management and data analytics coursework. Includes practice CDs.",
            "category": "Books",
            "condition": "Good",
            "quantity_total": 14,
            "quantity_available": 14,
            "quantity_reserved": 0,
            "unit": "copies",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "loyola_breadboards",
            "college": colleges_by_name["Loyola College"],
            "creator": users_by_email["rajesh.kannan@example.edu"],
            "name": "Electronic Circuit Breadboards & Digital Multimeters",
            "description": "Solderless 830-tie point breadboards with autoranging digital multimeters and test leads.",
            "category": "Electronics",
            "condition": "Good",
            "quantity_total": 20,
            "quantity_available": 20,
            "quantity_reserved": 0,
            "unit": "sets",
            "transfer_type": "exchange",
            "indicative_price": None,
            "status": "active",
        },
        {
            "key": "loyola_drafting",
            "college": colleges_by_name["Loyola College"],
            "creator": users_by_email["rep.loyola@example.edu"],
            "name": "A3 Technical Drawing Boards & Drafting Scales",
            "description": "Parallel motion drafting boards with drafting squares and metric triangular architect scales.",
            "category": "Other",
            "condition": "Good",
            "quantity_total": 16,
            "quantity_available": 16,
            "quantity_reserved": 0,
            "unit": "sets",
            "transfer_type": "donation",
            "indicative_price": None,
            "status": "active",
        },
    ]

    resources_by_key: dict[str, Resource] = {}
    for r_def in resource_definitions:
        existing = db.scalar(
            select(Resource).where(
                Resource.college_id == r_def["college"].id,
                Resource.name == r_def["name"],
            )
        )
        if existing is None:
            created = Resource(
                college_id=r_def["college"].id,
                created_by_user_id=r_def["creator"].id,
                name=r_def["name"],
                description=r_def["description"],
                category=r_def["category"],
                condition=r_def["condition"],
                quantity_total=r_def["quantity_total"],
                quantity_available=r_def["quantity_available"],
                quantity_reserved=r_def["quantity_reserved"],
                unit=r_def["unit"],
                transfer_type=r_def["transfer_type"],
                indicative_price=r_def["indicative_price"],
                status=r_def["status"],
                created_at=_utc(days_ago=20),
                updated_at=_utc(days_ago=2),
            )
            db.add(created)
            db.flush()
            resources_by_key[r_def["key"]] = created
            manifest_records["resources"].append({"id": created.id, "name": created.name, "college_id": created.college_id})
            print(f"  + Resource created: {created.name} (ID {created.id})")
        else:
            resources_by_key[r_def["key"]] = existing
            manifest_records["resources"].append({"id": existing.id, "name": existing.name, "college_id": existing.college_id})
            print(f"  = Resource exists: {existing.name} (ID {existing.id})")

    # -------------------------------------------------------------------------
    # 4. Requests (Comprehensive workflow branches)
    # -------------------------------------------------------------------------
    request_definitions = [
        # Req 1: Pending Donation
        {
            "key": "req_clrs_pending",
            "resource": resources_by_key["anna_clrs"],
            "requesting_college": colleges_by_name["Loyola College"],
            "requester": users_by_email["rep.loyola@example.edu"],
            "offered_resource": None,
            "requested_quantity": 3,
            "offered_quantity": None,
            "request_type": "donation",
            "purpose": "Provide reference copies for new BCA data structures lab reference corner.",
            "status": "pending",
            "approved_quantity": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "rejection_reason": None,
            "created_at": _utc(days_ago=3),
        },
        # Req 2: Approved Donation (Full Approval with active reservation)
        {
            "key": "req_clrs_approved",
            "resource": resources_by_key["anna_clrs"],
            "requesting_college": colleges_by_name["University of Madras"],
            "requester": users_by_email["rep.unom@example.edu"],
            "offered_resource": None,
            "requested_quantity": 5,
            "offered_quantity": None,
            "request_type": "donation",
            "purpose": "Support postgraduate computer science competitive programming seminar.",
            "status": "approved",
            "approved_quantity": 5,
            "reviewed_by": users_by_email["rep.anna@example.edu"],
            "reviewed_at": _utc(days_ago=2),
            "rejection_reason": None,
            "created_at": _utc(days_ago=5),
        },
        # Req 3: Approved Donation (Partial Approval with active reservation)
        {
            "key": "req_calc_partial",
            "resource": resources_by_key["anna_calculators"],
            "requesting_college": colleges_by_name["Loyola College"],
            "requester": users_by_email["deepa.natarajan@example.edu"],
            "offered_resource": None,
            "requested_quantity": 6,
            "offered_quantity": None,
            "request_type": "donation",
            "purpose": "Assist underprivileged students during end-semester engineering mathematics exam.",
            "status": "approved",
            "approved_quantity": 4,  # Partial approval (4 out of 6)
            "reviewed_by": users_by_email["rep.anna@example.edu"],
            "reviewed_at": _utc(days_ago=4),
            "rejection_reason": None,
            "created_at": _utc(days_ago=6),
        },
        # Req 4: Rejected Donation
        {
            "key": "req_micro_rejected",
            "resource": resources_by_key["iitm_microscopes"],
            "requesting_college": colleges_by_name["University of Madras"],
            "requester": users_by_email["karthik.balaji@example.edu"],
            "offered_resource": None,
            "requested_quantity": 2,
            "offered_quantity": None,
            "request_type": "donation",
            "purpose": "Supplementary microscopy equipment for biochemistry practical classes.",
            "status": "rejected",
            "approved_quantity": None,
            "reviewed_by": users_by_email["rep.iitm@example.edu"],
            "reviewed_at": _utc(days_ago=7),
            "rejection_reason": "Currently reserved for internal postgraduate histology laboratory practicals.",
            "created_at": _utc(days_ago=9),
        },
        # Req 5: Pending Exchange
        {
            "key": "req_rpi_exchange_pending",
            "resource": resources_by_key["iitm_rpi"],
            "requesting_college": colleges_by_name["Anna University"],
            "requester": users_by_email["priya.sundaram@example.edu"],
            "offered_resource": resources_by_key["anna_oscilloscope"],
            "requested_quantity": 2,
            "offered_quantity": 2,
            "request_type": "exchange",
            "purpose": "Exchange digital storage oscilloscope units for IoT robotics workshop kits.",
            "status": "pending",
            "approved_quantity": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "rejection_reason": None,
            "created_at": _utc(days_ago=1),
        },
        # Req 6: Approved Exchange (Both resources reserved)
        {
            "key": "req_rpi_exchange_approved",
            "resource": resources_by_key["iitm_rpi"],
            "requesting_college": colleges_by_name["University of Madras"],
            "requester": users_by_email["karthik.balaji@example.edu"],
            "offered_resource": resources_by_key["unom_arduino"],
            "requested_quantity": 4,
            "offered_quantity": 4,
            "request_type": "exchange",
            "purpose": "Exchange 4 Arduino starter sensor kits for 4 Raspberry Pi 4 systems for senior capstone lab.",
            "status": "approved",
            "approved_quantity": 4,
            "reviewed_by": users_by_email["rep.iitm@example.edu"],
            "reviewed_at": _utc(days_ago=3),
            "rejection_reason": None,
            "created_at": _utc(days_ago=5),
        },
        # Req 7: Pending Purchase Enquiry
        {
            "key": "req_stm32_purchase_pending",
            "resource": resources_by_key["anna_stm32"],
            "requesting_college": colleges_by_name["Loyola College"],
            "requester": users_by_email["rajesh.kannan@example.edu"],
            "offered_resource": None,
            "requested_quantity": 5,
            "offered_quantity": None,
            "request_type": "purchase_enquiry",
            "purpose": "Acquire 5 STM32 Nucleo boards at institutional discount price for embedded systems elective.",
            "status": "pending",
            "approved_quantity": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "rejection_reason": None,
            "created_at": _utc(days_ago=2),
        },
        # Req 8: Approved Purchase Enquiry (Intent confirmed by buyer & approved by seller)
        {
            "key": "req_fpga_purchase_approved",
            "resource": resources_by_key["iitm_fpga"],
            "requesting_college": colleges_by_name["University of Madras"],
            "requester": users_by_email["rep.unom@example.edu"],
            "offered_resource": None,
            "requested_quantity": 2,
            "offered_quantity": None,
            "request_type": "purchase_enquiry",
            "purpose": "Procure 2 Spartan-7 FPGA development boards for VLSI architecture laboratory.",
            "status": "approved",
            "approved_quantity": 2,
            "reviewed_by": users_by_email["rep.iitm@example.edu"],
            "reviewed_at": _utc(days_ago=3),
            "purchase_intent_confirmed_at": _utc(days_ago=4),
            "purchase_confirmed_by": users_by_email["rep.unom@example.edu"],
            "rejection_reason": None,
            "created_at": _utc(days_ago=6),
        },
        # Req 9: In-Progress Request with active in-transit transfer
        {
            "key": "req_slides_in_progress",
            "resource": resources_by_key["loyola_slides"],
            "requesting_college": colleges_by_name["Anna University"],
            "requester": users_by_email["priya.sundaram@example.edu"],
            "offered_resource": None,
            "requested_quantity": 2,
            "offered_quantity": None,
            "request_type": "donation",
            "purpose": "Environmental biotechnology lab reference slide sets for student microscopy training.",
            "status": "in_progress",
            "approved_quantity": 2,
            "reviewed_by": users_by_email["rep.loyola@example.edu"],
            "reviewed_at": _utc(days_ago=4),
            "rejection_reason": None,
            "created_at": _utc(days_ago=7),
        },
        # Req 10: Completed Request (Successfully received and confirmed)
        {
            "key": "req_prml_completed",
            "resource": resources_by_key["iitm_prml"],
            "requesting_college": colleges_by_name["University of Madras"],
            "requester": users_by_email["karthik.balaji@example.edu"],
            "offered_resource": None,
            "requested_quantity": 4,
            "offered_quantity": None,
            "request_type": "donation",
            "purpose": "Machine learning research reading group reference library.",
            "status": "completed",
            "approved_quantity": 4,
            "reviewed_by": users_by_email["rep.iitm@example.edu"],
            "reviewed_at": _utc(days_ago=14),
            "rejection_reason": None,
            "created_at": _utc(days_ago=18),
        },
        # Req 11: Disputed Request (Delivered with damage/missing items, dispute open)
        {
            "key": "req_calipers_disputed",
            "resource": resources_by_key["iitm_calipers"],
            "requesting_college": colleges_by_name["Anna University"],
            "requester": users_by_email["rep.anna@example.edu"],
            "offered_resource": None,
            "requested_quantity": 5,
            "offered_quantity": None,
            "request_type": "donation",
            "purpose": "Precision measurement instruments for mechanical workshop batch.",
            "status": "awaiting_resolution",
            "approved_quantity": 5,
            "reviewed_by": users_by_email["rep.iitm@example.edu"],
            "reviewed_at": _utc(days_ago=8),
            "rejection_reason": None,
            "created_at": _utc(days_ago=12),
        },
        # Req 12: Dispute Resolved Request (Platform admin reviewed & resolved)
        {
            "key": "req_clayden_resolved",
            "resource": resources_by_key["unom_clayden"],
            "requesting_college": colleges_by_name["Loyola College"],
            "requester": users_by_email["deepa.natarajan@example.edu"],
            "offered_resource": None,
            "requested_quantity": 4,
            "offered_quantity": None,
            "request_type": "donation",
            "purpose": "M.Sc. Chemistry organic synthesis reference curriculum.",
            "status": "completed",
            "approved_quantity": 4,
            "reviewed_by": users_by_email["rep.unom@example.edu"],
            "reviewed_at": _utc(days_ago=15),
            "rejection_reason": None,
            "created_at": _utc(days_ago=20),
        },
        # Req 13: Cancelled Request (Pre-dispatch cancellation approved)
        {
            "key": "req_dsa_cancelled",
            "resource": resources_by_key["unom_dsa_notes"],
            "requesting_college": colleges_by_name["Loyola College"],
            "requester": users_by_email["rajesh.kannan@example.edu"],
            "offered_resource": None,
            "requested_quantity": 3,
            "offered_quantity": None,
            "request_type": "donation",
            "purpose": "Supplemental tutorial booklets for third-year computer science students.",
            "status": "cancelled",
            "approved_quantity": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "rejection_reason": None,
            "cancellation_requested_by": users_by_email["rajesh.kannan@example.edu"],
            "cancellation_requested_at": _utc(days_ago=5),
            "cancellation_reason": "Department syllabus revised for current semester; alternative notes selected.",
            "cancellation_reviewed_by": users_by_email["rep.unom@example.edu"],
            "cancellation_reviewed_at": _utc(days_ago=4),
            "cancellation_previous_status": "pending",
            "cancellation_decision": "approved",
            "created_at": _utc(days_ago=8),
        },
        # Req 14: Rejected Cancellation Request
        {
            "key": "req_cuvettes_canc_rejected",
            "resource": resources_by_key["unom_cuvettes"],
            "requesting_college": colleges_by_name["Anna University"],
            "requester": users_by_email["priya.sundaram@example.edu"],
            "offered_resource": None,
            "requested_quantity": 2,
            "offered_quantity": None,
            "request_type": "purchase_enquiry",
            "purpose": "Spectrophotometry calibration for analytical chemistry workshop.",
            "status": "approved",
            "approved_quantity": 2,
            "reviewed_by": users_by_email["rep.unom@example.edu"],
            "reviewed_at": _utc(days_ago=6),
            "purchase_intent_confirmed_at": _utc(days_ago=7),
            "purchase_confirmed_by": users_by_email["priya.sundaram@example.edu"],
            "rejection_reason": None,
            "cancellation_requested_by": users_by_email["priya.sundaram@example.edu"],
            "cancellation_requested_at": _utc(days_ago=4),
            "cancellation_reason": "Budget realignment enquiry.",
            "cancellation_reviewed_by": users_by_email["rep.unom@example.edu"],
            "cancellation_reviewed_at": _utc(days_ago=3),
            "cancellation_previous_status": "approved",
            "cancellation_decision": "rejected",
            "created_at": _utc(days_ago=9),
        },
    ]

    requests_by_key: dict[str, Request] = {}
    for req_def in request_definitions:
        existing = db.scalar(
            select(Request).where(
                Request.requesting_college_id == req_def["requesting_college"].id,
                Request.resource_id == req_def["resource"].id,
                Request.purpose == req_def["purpose"],
            )
        )
        if existing is None:
            created = Request(
                resource_id=req_def["resource"].id,
                requesting_college_id=req_def["requesting_college"].id,
                requested_by_user_id=req_def["requester"].id,
                offered_resource_id=req_def["offered_resource"].id if req_def["offered_resource"] else None,
                requested_quantity=req_def["requested_quantity"],
                offered_quantity=req_def["offered_quantity"],
                request_type=req_def["request_type"],
                purpose=req_def["purpose"],
                status=req_def["status"],
                approved_quantity=req_def["approved_quantity"],
                reviewed_by_user_id=req_def["reviewed_by"].id if req_def.get("reviewed_by") else None,
                reviewed_at=req_def.get("reviewed_at"),
                purchase_intent_confirmed_at=req_def.get("purchase_intent_confirmed_at"),
                purchase_confirmed_by_user_id=req_def["purchase_confirmed_by"].id if req_def.get("purchase_confirmed_by") else None,
                rejection_reason=req_def.get("rejection_reason"),
                cancellation_requested_by_user_id=req_def["cancellation_requested_by"].id if req_def.get("cancellation_requested_by") else None,
                cancellation_requested_at=req_def.get("cancellation_requested_at"),
                cancellation_reason=req_def.get("cancellation_reason"),
                cancellation_reviewed_by_user_id=req_def["cancellation_reviewed_by"].id if req_def.get("cancellation_reviewed_by") else None,
                cancellation_reviewed_at=req_def.get("cancellation_reviewed_at"),
                cancellation_previous_status=req_def.get("cancellation_previous_status"),
                cancellation_decision=req_def.get("cancellation_decision"),
                created_at=req_def["created_at"],
                updated_at=_utc(hours_ago=2),
            )
            db.add(created)
            db.flush()
            requests_by_key[req_def["key"]] = created
            manifest_records["requests"].append({"id": created.id, "key": req_def["key"], "status": created.status})
            print(f"  + Request created: [{created.status}] {created.purpose[:45]}... (ID {created.id})")
        else:
            requests_by_key[req_def["key"]] = existing
            manifest_records["requests"].append({"id": existing.id, "key": req_def["key"], "status": existing.status})
            print(f"  = Request exists: (ID {existing.id})")

    # -------------------------------------------------------------------------
    # 5. Inter-College Transfers & Status History
    # -------------------------------------------------------------------------
    transfer_definitions = [
        # Transfer 1: In-Transit (Dispatched)
        {
            "key": "tr_slides_dispatched",
            "request": requests_by_key["req_slides_in_progress"],
            "resource": resources_by_key["loyola_slides"],
            "transfer_leg": "requested_resource",
            "source_college": colleges_by_name["Loyola College"],
            "destination_college": colleges_by_name["Anna University"],
            "quantity": 2,
            "quantity_received_good": None,
            "quantity_damaged": None,
            "quantity_missing": None,
            "status": "dispatched",
            "dispute_status": "none",
            "dispute_resolution": None,
            "dispute_outcome": None,
            "creator": users_by_email["rep.loyola@example.edu"],
            "dispatcher": users_by_email["rep.loyola@example.edu"],
            "receiver": None,
            "pickup_or_delivery_date": _utc(days_ago=1),
            "dispatch_notes": "Dispatched via Professional Courier Chennai Campus Express, Waybill #CC-CHE-98214. Fragile optical glassware pack.",
            "receipt_confirmation": None,
            "received_at": None,
            "created_at": _utc(days_ago=3),
            "completed_at": None,
            "history": [
                {"previous_status": None, "new_status": "preparing", "notes": "Batch transfer initialized by sending institution.", "days_ago": 3},
                {"previous_status": "preparing", "new_status": "dispatched", "notes": "Dispatched via Professional Courier #CC-CHE-98214.", "days_ago": 1},
            ],
        },
        # Transfer 2: Completed Delivery
        {
            "key": "tr_prml_completed",
            "request": requests_by_key["req_prml_completed"],
            "resource": resources_by_key["iitm_prml"],
            "transfer_leg": "requested_resource",
            "source_college": colleges_by_name["Indian Institute of Technology Madras"],
            "destination_college": colleges_by_name["University of Madras"],
            "quantity": 4,
            "quantity_received_good": 4,
            "quantity_damaged": 0,
            "quantity_missing": 0,
            "status": "completed",
            "dispute_status": "none",
            "dispute_resolution": None,
            "dispute_outcome": None,
            "creator": users_by_email["rep.iitm@example.edu"],
            "dispatcher": users_by_email["rep.iitm@example.edu"],
            "receiver": users_by_email["rep.unom@example.edu"],
            "pickup_or_delivery_date": _utc(days_ago=12),
            "dispatch_notes": "Hand-delivered by campus courier to Guindy Science Library receiving section.",
            "receipt_confirmation": "All 4 volumes verified in excellent condition and accessioned into seminar library.",
            "received_at": _utc(days_ago=10),
            "created_at": _utc(days_ago=13),
            "completed_at": _utc(days_ago=10),
            "history": [
                {"previous_status": None, "new_status": "preparing", "notes": "Books packaged in protective wrap.", "days_ago": 13},
                {"previous_status": "preparing", "new_status": "dispatched", "notes": "Handover to inter-campus messenger.", "days_ago": 12},
                {"previous_status": "dispatched", "new_status": "received", "notes": "Verified 4 of 4 good condition.", "days_ago": 10},
                {"previous_status": "received", "new_status": "completed", "notes": "Transfer complete.", "days_ago": 10},
            ],
        },
        # Transfer 3: Disputed Delivery (Open Dispute with Damaged & Missing Items)
        {
            "key": "tr_calipers_disputed",
            "request": requests_by_key["req_calipers_disputed"],
            "resource": resources_by_key["iitm_calipers"],
            "transfer_leg": "requested_resource",
            "source_college": colleges_by_name["Indian Institute of Technology Madras"],
            "destination_college": colleges_by_name["Anna University"],
            "quantity": 5,
            "quantity_received_good": 3,
            "quantity_damaged": 1,
            "quantity_missing": 1,
            "status": "disputed",
            "dispute_status": "open",
            "dispute_resolution": None,
            "dispute_outcome": None,
            "creator": users_by_email["rep.iitm@example.edu"],
            "dispatcher": users_by_email["anand.venkatesh@example.edu"],
            "receiver": users_by_email["rep.anna@example.edu"],
            "pickup_or_delivery_date": _utc(days_ago=6),
            "dispatch_notes": "Shipped via Speed Post Parcel #SP-CHE-441092.",
            "receipt_confirmation": "Inspection report: 3 calipers verified intact and calibrated. 1 micrometer thimble cracked in transit; 1 depth gauge case empty upon unboxing.",
            "received_at": _utc(days_ago=4),
            "created_at": _utc(days_ago=7),
            "completed_at": None,
            "history": [
                {"previous_status": None, "new_status": "preparing", "notes": "Instruments packed in protective wooden crate.", "days_ago": 7},
                {"previous_status": "preparing", "new_status": "dispatched", "notes": "Parcel booked at Guindy Post Office.", "days_ago": 6},
                {"previous_status": "dispatched", "new_status": "disputed", "notes": "Dispute filed by receiving institution: 1 damaged, 1 missing.", "days_ago": 4},
            ],
        },
        # Transfer 4: Dispute Resolved Delivery (Platform Admin Resolved)
        {
            "key": "tr_clayden_resolved",
            "request": requests_by_key["req_clayden_resolved"],
            "resource": resources_by_key["unom_clayden"],
            "transfer_leg": "requested_resource",
            "source_college": colleges_by_name["University of Madras"],
            "destination_college": colleges_by_name["Loyola College"],
            "quantity": 4,
            "quantity_received_good": 3,
            "quantity_damaged": 1,
            "quantity_missing": 0,
            "status": "completed",
            "dispute_status": "resolved",
            "dispute_outcome": "accept_report",
            "dispute_resolution": "Platform Admin reviewed inspection photographs of binding damage. Accepted 3 good copies as final receipt; inventory adjusted accordingly.",
            "creator": users_by_email["rep.unom@example.edu"],
            "dispatcher": users_by_email["rep.unom@example.edu"],
            "receiver": users_by_email["rep.loyola@example.edu"],
            "pickup_or_delivery_date": _utc(days_ago=14),
            "dispatch_notes": "Direct campus delivery to Chemistry Department office.",
            "receipt_confirmation": "Received 3 clean copies. 1 copy suffered water damage to outer rear cover.",
            "received_at": _utc(days_ago=11),
            "created_at": _utc(days_ago=14),
            "completed_at": _utc(days_ago=9),
            "history": [
                {"previous_status": None, "new_status": "preparing", "notes": "Transfer batch registered.", "days_ago": 14},
                {"previous_status": "preparing", "new_status": "dispatched", "notes": "Dispatched via campus transport.", "days_ago": 14},
                {"previous_status": "dispatched", "new_status": "disputed", "notes": "Receipt inspection reported 1 damaged volume.", "days_ago": 11},
                {"previous_status": "disputed", "new_status": "completed", "notes": "Dispute resolved by Platform Admin with outcome accept_report.", "days_ago": 9},
            ],
        },
    ]

    for tr_def in transfer_definitions:
        existing = db.scalar(
            select(Transfer).where(
                Transfer.request_id == tr_def["request"].id,
                Transfer.transfer_leg == tr_def["transfer_leg"],
            )
        )
        if existing is None:
            created = Transfer(
                request_id=tr_def["request"].id,
                resource_id=tr_def["resource"].id,
                transfer_leg=tr_def["transfer_leg"],
                source_college_id=tr_def["source_college"].id,
                destination_college_id=tr_def["destination_college"].id,
                quantity=tr_def["quantity"],
                quantity_received_good=tr_def["quantity_received_good"],
                quantity_damaged=tr_def["quantity_damaged"],
                quantity_missing=tr_def["quantity_missing"],
                status=tr_def["status"],
                dispute_status=tr_def["dispute_status"],
                dispute_resolution=tr_def["dispute_resolution"],
                dispute_outcome=tr_def["dispute_outcome"],
                dispute_resolved_by_user_id=users_by_email["admin@example.edu"].id if tr_def["dispute_outcome"] else None,
                dispute_resolved_at=_utc(days_ago=9) if tr_def["dispute_outcome"] else None,
                created_by_user_id=tr_def["creator"].id,
                dispatched_by_user_id=tr_def["dispatcher"].id if tr_def["dispatcher"] else None,
                received_by_user_id=tr_def["receiver"].id if tr_def["receiver"] else None,
                pickup_or_delivery_date=tr_def["pickup_or_delivery_date"],
                dispatch_notes=tr_def["dispatch_notes"],
                receipt_confirmation=tr_def["receipt_confirmation"],
                received_at=tr_def["received_at"],
                created_at=tr_def["created_at"],
                completed_at=tr_def["completed_at"],
            )
            db.add(created)
            db.flush()
            manifest_records["transfers"].append({"id": created.id, "key": tr_def["key"], "status": created.status})
            print(f"  + Transfer created: [{created.status}] (ID {created.id})")

            # Status history entries
            for h in tr_def["history"]:
                history_entry = TransferStatusHistory(
                    transfer_id=created.id,
                    changed_by_user_id=tr_def["creator"].id,
                    actor_type="user",
                    previous_status=h["previous_status"],
                    new_status=h["new_status"],
                    notes=h["notes"],
                    changed_at=_utc(days_ago=h["days_ago"]),
                )
                db.add(history_entry)
                db.flush()
                manifest_records["transfer_history"].append({"id": history_entry.id, "transfer_id": created.id, "status": h["new_status"]})
        else:
            manifest_records["transfers"].append({"id": existing.id, "key": tr_def["key"], "status": existing.status})
            for h in existing.status_history:
                manifest_records["transfer_history"].append({"id": h.id, "transfer_id": existing.id, "status": h.new_status})
            print(f"  = Transfer exists: (ID {existing.id})")

    db.commit()

    # Save manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_data = {
        "seeded_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "colleges": len(manifest_records["colleges"]),
            "users": len(manifest_records["users"]),
            "resources": len(manifest_records["resources"]),
            "requests": len(manifest_records["requests"]),
            "transfers": len(manifest_records["transfers"]),
            "transfer_history": len(manifest_records["transfer_history"]),
        },
        "records": manifest_records,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print("Seeding completed successfully. Manifest written to:", manifest_path)
    return manifest_data


def rollback_demo_data(db: Session, *, manifest_path: Path = MANIFEST_PATH) -> dict[str, int]:
    """Safely roll back only the records created by the demo seeder using the recorded manifest."""
    if not manifest_path.exists():
        print(f"No seed manifest found at {manifest_path}; nothing to roll back.")
        return {"deleted": 0}

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    records = manifest_data.get("records", {})
    counts = {}

    print("Rolling back CampusCycle demonstration records...")

    # Delete in reverse topological order (respecting foreign keys)
    # 1. Transfer history
    history_ids = [r["id"] for r in records.get("transfer_history", [])]
    if history_ids:
        del_h = db.query(TransferStatusHistory).filter(TransferStatusHistory.id.in_(history_ids)).delete(synchronize_session=False)
        counts["transfer_history"] = del_h
        print(f"  - Deleted {del_h} transfer history records.")

    # 2. Transfers
    transfer_ids = [r["id"] for r in records.get("transfers", [])]
    if transfer_ids:
        del_t = db.query(Transfer).filter(Transfer.id.in_(transfer_ids)).delete(synchronize_session=False)
        counts["transfers"] = del_t
        print(f"  - Deleted {del_t} transfers.")

    # 3. Requests
    request_ids = [r["id"] for r in records.get("requests", [])]
    if request_ids:
        del_req = db.query(Request).filter(Request.id.in_(request_ids)).delete(synchronize_session=False)
        counts["requests"] = del_req
        print(f"  - Deleted {del_req} requests.")

    # 4. Resources
    resource_ids = [r["id"] for r in records.get("resources", [])]
    if resource_ids:
        del_res = db.query(Resource).filter(Resource.id.in_(resource_ids)).delete(synchronize_session=False)
        counts["resources"] = del_res
        print(f"  - Deleted {del_res} resources.")

    # 5. Users
    user_ids = [r["id"] for r in records.get("users", [])]
    if user_ids:
        del_u = db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        counts["users"] = del_u
        print(f"  - Deleted {del_u} users.")

    # 6. Colleges
    college_ids = [r["id"] for r in records.get("colleges", [])]
    if college_ids:
        del_c = db.query(College).filter(College.id.in_(college_ids)).delete(synchronize_session=False)
        counts["colleges"] = del_c
        print(f"  - Deleted {del_c} colleges.")

    db.commit()
    manifest_path.unlink(missing_ok=True)
    print("Rollback complete. Manifest removed.")
    return counts
