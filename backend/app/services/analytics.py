from typing import Any
from fastapi import HTTPException
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models import College, Request, Resource, Transfer, User
from app.schemas.analytics import (
    AnalyticsSummaryData,
    CategoryAnalyticsData,
    CategoryMetricItem,
    CollegeAnalyticsData,
    CollegeSummaryMetrics,
    RequestAnalyticsData,
    RequestStatusCountItem,
    RequestSummaryMetrics,
    RequestTypeCountItem,
    ResourceSummaryMetrics,
    TopParticipatingCollegeItem,
    TransferAnalyticsData,
    TransferDisputeMetrics,
    TransferLegCountItem,
    TransferQuantityMetrics,
    TransferStatusCountItem,
    TransferSummaryMetrics,
)


def _get_target_college_id(actor: User) -> int | None:
    if actor.role == "platform_admin":
        return None
    if actor.role == "college_representative" and actor.college_id is not None:
        return actor.college_id
    raise HTTPException(status_code=403, detail="Authorized college user access required.")


def get_summary_analytics(db: Session, *, actor: User) -> dict[str, Any]:
    college_id = _get_target_college_id(actor)
    scope = "global" if college_id is None else "college"

    # 1. College Summary Metrics (Global only)
    college_metrics = None
    verification_status = None
    if scope == "global":
        col_row = db.execute(
            select(
                func.count(College.id).label("total"),
                func.count(case((College.verification_status == "verified", 1))).label("verified"),
                func.count(case((College.verification_status == "pending", 1))).label("pending"),
                func.count(case((College.verification_status == "rejected", 1))).label("rejected"),
            )
        ).one()
        college_metrics = CollegeSummaryMetrics(
            total_colleges=col_row.total or 0,
            verified_colleges=col_row.verified or 0,
            pending_colleges=col_row.pending or 0,
            rejected_colleges=col_row.rejected or 0,
        )
    else:
        current_college = db.get(College, college_id)
        if current_college:
            verification_status = current_college.verification_status

    # 2. Resource Summary Metrics
    res_query = select(
        func.count(Resource.id).label("total"),
        func.count(case((Resource.status == "active", 1))).label("active"),
        func.count(case((Resource.status == "inactive", 1))).label("inactive"),
        func.count(case((Resource.status == "depleted", 1))).label("depleted"),
        func.coalesce(func.sum(Resource.quantity_total), 0).label("qty_total"),
        func.coalesce(func.sum(Resource.quantity_available), 0).label("qty_available"),
        func.coalesce(func.sum(Resource.quantity_reserved), 0).label("qty_reserved"),
    )
    if college_id is not None:
        res_query = res_query.where(Resource.college_id == college_id)
    res_row = db.execute(res_query).one()

    resource_metrics = ResourceSummaryMetrics(
        total_listings=res_row.total or 0,
        active_listings=res_row.active or 0,
        inactive_listings=res_row.inactive or 0,
        depleted_listings=res_row.depleted or 0,
        total_quantity=res_row.qty_total or 0,
        available_quantity=res_row.qty_available or 0,
        reserved_quantity=res_row.qty_reserved or 0,
    )

    # 3. Request Summary Metrics
    req_query = (
        select(
            func.count(Request.id).label("total"),
            func.count(case((Request.status == "pending", 1))).label("pending"),
            func.count(case((Request.status == "approved", 1))).label("approved"),
            func.count(case((Request.status == "rejected", 1))).label("rejected"),
            func.count(case((Request.status == "in_progress", 1))).label("in_progress"),
            func.count(case((Request.status == "awaiting_resolution", 1))).label("awaiting_resolution"),
            func.count(case((Request.status == "completed", 1))).label("completed"),
            func.count(case((Request.status == "cancelled", 1))).label("cancelled"),
        )
        .select_from(Request)
        .join(Resource, Request.resource_id == Resource.id)
    )

    incoming_requests = None
    outgoing_requests = None

    if college_id is not None:
        req_query = req_query.where(
            or_(Request.requesting_college_id == college_id, Resource.college_id == college_id)
        )
        # Counts by leg for representative
        in_out_row = db.execute(
            select(
                func.count(case((Resource.college_id == college_id, 1))).label("incoming"),
                func.count(case((Request.requesting_college_id == college_id, 1))).label("outgoing"),
            )
            .select_from(Request)
            .join(Resource, Request.resource_id == Resource.id)
            .where(or_(Request.requesting_college_id == college_id, Resource.college_id == college_id))
        ).one()
        incoming_requests = in_out_row.incoming or 0
        outgoing_requests = in_out_row.outgoing or 0

    req_row = db.execute(req_query).one()

    request_metrics = RequestSummaryMetrics(
        total_requests=req_row.total or 0,
        pending_requests=req_row.pending or 0,
        approved_requests=req_row.approved or 0,
        rejected_requests=req_row.rejected or 0,
        in_progress_requests=req_row.in_progress or 0,
        awaiting_resolution_requests=req_row.awaiting_resolution or 0,
        completed_requests=req_row.completed or 0,
        cancelled_requests=req_row.cancelled or 0,
        incoming_requests=incoming_requests,
        outgoing_requests=outgoing_requests,
    )

    # 4. Transfer Summary Metrics
    trans_query = select(
        func.count(Transfer.id).label("total"),
        func.count(case((Transfer.status == "preparing", 1))).label("preparing"),
        func.count(case((Transfer.status == "dispatched", 1))).label("dispatched"),
        func.count(case((Transfer.status == "partially_received", 1))).label("partially_received"),
        func.count(case((Transfer.status == "disputed", 1))).label("disputed"),
        func.count(case((Transfer.status == "received", 1))).label("received"),
        func.count(case((Transfer.status == "completed", 1))).label("completed"),
        func.count(case((Transfer.status == "cancellation_pending", 1))).label("cancellation_pending"),
        func.count(case((Transfer.status == "cancelled", 1))).label("cancelled"),
    )

    outbound_transfers = None
    inbound_transfers = None

    if college_id is not None:
        trans_query = trans_query.where(
            or_(Transfer.source_college_id == college_id, Transfer.destination_college_id == college_id)
        )
        in_out_trans = db.execute(
            select(
                func.count(case((Transfer.source_college_id == college_id, 1))).label("outbound"),
                func.count(case((Transfer.destination_college_id == college_id, 1))).label("inbound"),
            ).where(
                or_(Transfer.source_college_id == college_id, Transfer.destination_college_id == college_id)
            )
        ).one()
        outbound_transfers = in_out_trans.outbound or 0
        inbound_transfers = in_out_trans.inbound or 0

    trans_row = db.execute(trans_query).one()

    transfer_metrics = TransferSummaryMetrics(
        total_transfers=trans_row.total or 0,
        preparing_transfers=trans_row.preparing or 0,
        dispatched_transfers=trans_row.dispatched or 0,
        partially_received_transfers=trans_row.partially_received or 0,
        disputed_transfers=trans_row.disputed or 0,
        received_transfers=trans_row.received or 0,
        completed_transfers=trans_row.completed or 0,
        cancellation_pending_transfers=trans_row.cancellation_pending or 0,
        cancelled_transfers=trans_row.cancelled or 0,
        outbound_transfers=outbound_transfers,
        inbound_transfers=inbound_transfers,
    )

    data = AnalyticsSummaryData(
        scope=scope,
        college_id=college_id,
        verification_status=verification_status,
        colleges=college_metrics,
        resources=resource_metrics,
        requests=request_metrics,
        transfers=transfer_metrics,
    )
    return data.model_dump(mode="json")


def get_category_analytics(db: Session, *, actor: User) -> dict[str, Any]:
    college_id = _get_target_college_id(actor)
    scope = "global" if college_id is None else "college"

    query = select(
        Resource.category,
        func.count(Resource.id).label("total_listings"),
        func.count(case((Resource.status == "active", 1))).label("active_listings"),
        func.coalesce(func.sum(Resource.quantity_total), 0).label("total_quantity"),
        func.coalesce(func.sum(Resource.quantity_available), 0).label("available_quantity"),
        func.coalesce(func.sum(Resource.quantity_reserved), 0).label("reserved_quantity"),
    ).group_by(Resource.category).order_by(func.count(Resource.id).desc())

    if college_id is not None:
        query = query.where(Resource.college_id == college_id)

    rows = db.execute(query).all()
    items = [
        CategoryMetricItem(
            category=row.category,
            total_listings=row.total_listings or 0,
            active_listings=row.active_listings or 0,
            total_quantity=row.total_quantity or 0,
            available_quantity=row.available_quantity or 0,
            reserved_quantity=row.reserved_quantity or 0,
        )
        for row in rows
    ]

    data = CategoryAnalyticsData(
        scope=scope,
        college_id=college_id,
        items=items,
        total_categories=len(items),
    )
    return data.model_dump(mode="json")


def get_request_analytics(db: Session, *, actor: User) -> dict[str, Any]:
    college_id = _get_target_college_id(actor)
    scope = "global" if college_id is None else "college"

    base_filter = None
    if college_id is not None:
        base_filter = or_(Request.requesting_college_id == college_id, Resource.college_id == college_id)

    # 1. Total and quantities
    totals_query = (
        select(
            func.count(Request.id).label("total"),
            func.count(case((Request.status == "completed", 1))).label("completed"),
            func.coalesce(func.sum(Request.requested_quantity), 0).label("total_requested_qty"),
            func.coalesce(func.sum(Request.approved_quantity), 0).label("total_approved_qty"),
        )
        .select_from(Request)
        .join(Resource, Request.resource_id == Resource.id)
    )
    if base_filter is not None:
        totals_query = totals_query.where(base_filter)
    totals_row = db.execute(totals_query).one()

    total_requests = totals_row.total or 0
    completed_requests = totals_row.completed or 0
    fulfillment_rate = round((completed_requests / total_requests * 100), 1) if total_requests > 0 else 0.0

    # 2. Group by status
    status_query = (
        select(Request.status, func.count(Request.id).label("count"))
        .select_from(Request)
        .join(Resource, Request.resource_id == Resource.id)
        .group_by(Request.status)
        .order_by(Request.status)
    )
    if base_filter is not None:
        status_query = status_query.where(base_filter)
    status_rows = db.execute(status_query).all()
    by_status = [
        RequestStatusCountItem(status=row.status, count=row.count or 0)
        for row in status_rows
    ]

    # 3. Group by request_type
    type_query = (
        select(
            Request.request_type,
            func.count(Request.id).label("count"),
            func.coalesce(func.sum(Request.requested_quantity), 0).label("quantity"),
        )
        .select_from(Request)
        .join(Resource, Request.resource_id == Resource.id)
        .group_by(Request.request_type)
        .order_by(Request.request_type)
    )
    if base_filter is not None:
        type_query = type_query.where(base_filter)
    type_rows = db.execute(type_query).all()
    by_type = [
        RequestTypeCountItem(request_type=row.request_type, count=row.count or 0, quantity=row.quantity or 0)
        for row in type_rows
    ]

    sent_count = None
    received_count = None
    if college_id is not None:
        counts = db.execute(
            select(
                func.count(case((Request.requesting_college_id == college_id, 1))).label("sent"),
                func.count(case((Resource.college_id == college_id, 1))).label("received"),
            )
            .select_from(Request)
            .join(Resource, Request.resource_id == Resource.id)
            .where(base_filter)
        ).one()
        sent_count = counts.sent or 0
        received_count = counts.received or 0

    data = RequestAnalyticsData(
        scope=scope,
        college_id=college_id,
        total_requests=total_requests,
        by_status=by_status,
        by_type=by_type,
        total_requested_quantity=totals_row.total_requested_qty or 0,
        total_approved_quantity=totals_row.total_approved_qty or 0,
        fulfillment_rate=fulfillment_rate,
        sent_count=sent_count,
        received_count=received_count,
    )
    return data.model_dump(mode="json")


def get_transfer_analytics(db: Session, *, actor: User) -> dict[str, Any]:
    college_id = _get_target_college_id(actor)
    scope = "global" if college_id is None else "college"

    base_filter = None
    if college_id is not None:
        base_filter = or_(Transfer.source_college_id == college_id, Transfer.destination_college_id == college_id)

    # 1. Total and status grouping
    status_query = (
        select(
            Transfer.status,
            func.count(Transfer.id).label("count"),
            func.coalesce(func.sum(Transfer.quantity), 0).label("quantity"),
        )
        .group_by(Transfer.status)
        .order_by(Transfer.status)
    )
    if base_filter is not None:
        status_query = status_query.where(base_filter)
    status_rows = db.execute(status_query).all()
    by_status = [
        TransferStatusCountItem(status=row.status, count=row.count or 0, quantity=row.quantity or 0)
        for row in status_rows
    ]
    total_transfers = sum(item.count for item in by_status)

    # 2. Leg grouping
    leg_query = (
        select(
            Transfer.transfer_leg,
            func.count(Transfer.id).label("count"),
            func.coalesce(func.sum(Transfer.quantity), 0).label("quantity"),
        )
        .group_by(Transfer.transfer_leg)
        .order_by(Transfer.transfer_leg)
    )
    if base_filter is not None:
        leg_query = leg_query.where(base_filter)
    leg_rows = db.execute(leg_query).all()
    by_leg = [
        TransferLegCountItem(leg=row.transfer_leg, count=row.count or 0, quantity=row.quantity or 0)
        for row in leg_rows
    ]

    # 3. Disputes
    disp_query = select(
        func.count(case((Transfer.dispute_status != "none", 1))).label("total_disputed"),
        func.count(case((Transfer.dispute_status == "open", 1))).label("open_disputes"),
        func.count(case((Transfer.dispute_status == "resolved", 1))).label("resolved_disputes"),
        func.count(case((Transfer.dispute_outcome == "accept_report", 1))).label("accept_report"),
        func.count(case((Transfer.dispute_outcome == "replacement_approved", 1))).label("replacement_approved"),
        func.count(case((Transfer.dispute_outcome == "claim_rejected", 1))).label("claim_rejected"),
    )
    if base_filter is not None:
        disp_query = disp_query.where(base_filter)
    disp_row = db.execute(disp_query).one()

    dispute_metrics = TransferDisputeMetrics(
        total_disputed=disp_row.total_disputed or 0,
        open_disputes=disp_row.open_disputes or 0,
        resolved_disputes=disp_row.resolved_disputes or 0,
        outcomes={
            "accept_report": disp_row.accept_report or 0,
            "replacement_approved": disp_row.replacement_approved or 0,
            "claim_rejected": disp_row.claim_rejected or 0,
        },
    )

    # 4. Quantities
    qty_query = select(
        func.coalesce(func.sum(Transfer.quantity), 0).label("shipped"),
        func.coalesce(func.sum(Transfer.quantity_received_good), 0).label("received_good"),
        func.coalesce(func.sum(Transfer.quantity_damaged), 0).label("damaged"),
        func.coalesce(func.sum(Transfer.quantity_missing), 0).label("missing"),
    )
    if base_filter is not None:
        qty_query = qty_query.where(base_filter)
    qty_row = db.execute(qty_query).one()

    quantity_metrics = TransferQuantityMetrics(
        total_shipped=qty_row.shipped or 0,
        received_good=qty_row.received_good or 0,
        damaged=qty_row.damaged or 0,
        missing=qty_row.missing or 0,
    )

    outbound_count = None
    inbound_count = None
    if college_id is not None:
        in_out = db.execute(
            select(
                func.count(case((Transfer.source_college_id == college_id, 1))).label("outbound"),
                func.count(case((Transfer.destination_college_id == college_id, 1))).label("inbound"),
            ).where(base_filter)
        ).one()
        outbound_count = in_out.outbound or 0
        inbound_count = in_out.inbound or 0

    data = TransferAnalyticsData(
        scope=scope,
        college_id=college_id,
        total_transfers=total_transfers,
        by_status=by_status,
        by_leg=by_leg,
        dispute_metrics=dispute_metrics,
        quantity_metrics=quantity_metrics,
        outbound_count=outbound_count,
        inbound_count=inbound_count,
    )
    return data.model_dump(mode="json")


def get_college_analytics(db: Session, *, actor: User) -> dict[str, Any]:
    if actor.role != "platform_admin" or actor.college_id is not None:
        raise HTTPException(status_code=403, detail="Platform administrator access is required.")

    # 1. Verification breakdown
    status_row = db.execute(
        select(
            func.count(College.id).label("total"),
            func.count(case((College.verification_status == "verified", 1))).label("verified"),
            func.count(case((College.verification_status == "pending", 1))).label("pending"),
            func.count(case((College.verification_status == "rejected", 1))).label("rejected"),
        )
    ).one()

    # 2. Colleges with active listings
    colleges_with_active = db.scalar(
        select(func.count(func.distinct(Resource.college_id)))
        .where(Resource.status == "active")
    ) or 0

    # 3. Colleges with completed transfers (source or destination)
    dest_completed_colleges = db.scalars(
        select(Transfer.destination_college_id)
        .where(Transfer.status == "completed")
        .distinct()
    ).all()
    src_completed_colleges = db.scalars(
        select(Transfer.source_college_id)
        .where(Transfer.status == "completed")
        .distinct()
    ).all()
    total_distinct_completed_colleges = len(set(src_completed_colleges) | set(dest_completed_colleges))

    # 4. Top participating verified colleges
    verified_colleges = db.scalars(
        select(College).where(College.verification_status == "verified").order_by(College.id)
    ).all()

    # Pre-aggregate active listings
    active_map = dict(
        db.execute(
            select(Resource.college_id, func.count(Resource.id))
            .where(Resource.status == "active")
            .group_by(Resource.college_id)
        ).all()
    )

    # Pre-aggregate completed transfers as source
    completed_src_map = dict(
        db.execute(
            select(Transfer.source_college_id, func.count(Transfer.id))
            .where(Transfer.status == "completed")
            .group_by(Transfer.source_college_id)
        ).all()
    )

    # Pre-aggregate completed transfers as destination
    completed_dst_map = dict(
        db.execute(
            select(Transfer.destination_college_id, func.count(Transfer.id))
            .where(Transfer.status == "completed")
            .group_by(Transfer.destination_college_id)
        ).all()
    )

    top_items = []
    for col in verified_colleges:
        active_count = active_map.get(col.id, 0)
        completed_count = completed_src_map.get(col.id, 0) + completed_dst_map.get(col.id, 0)
        top_items.append(
            TopParticipatingCollegeItem(
                id=col.id,
                name=col.name,
                city=col.city,
                verification_status=col.verification_status,
                active_listings_count=active_count,
                completed_transfers_count=completed_count,
            )
        )

    # Sort by active listings + completed transfers descending
    top_items.sort(key=lambda x: (x.active_listings_count + x.completed_transfers_count, x.id), reverse=True)

    data = CollegeAnalyticsData(
        total_colleges=status_row.total or 0,
        verified_colleges=status_row.verified or 0,
        pending_colleges=status_row.pending or 0,
        rejected_colleges=status_row.rejected or 0,
        colleges_with_active_listings=colleges_with_active,
        colleges_with_completed_transfers=total_distinct_completed_colleges,
        top_participating_colleges=top_items[:10],
    )
    return data.model_dump(mode="json")
