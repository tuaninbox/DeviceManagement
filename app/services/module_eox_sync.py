from datetime import datetime, timezone
from app.services.job_manager import update_job
from app.models import devices
from core.eox import get_eox_data_from_sn

def run_module_eox_sync(job_id, serials, db_session_factory):
    update_job(job_id, status="running", started_at=datetime.now(timezone.utc))

    session = db_session_factory()

    try:
        # Step 1: Call Cisco EoX API
        try:
            eox_results = get_eox_data_from_sn(serials)
        except Exception as e:
            update_job(
                job_id,
                status="failed",
                finished_at=datetime.now(timezone.utc),
                error=f"EoX API error: {e}",
            )
            return

        serial_data_list = eox_results.get("serial_numbers", [])

        # Step 2: Update DB
        updated_modules = []
        errors = []

        modules_for_update = (
            session.query(devices.Module)
            .filter(devices.Module.serial_number.in_(serials))
            .all()
        )

        for m in modules_for_update:
            try:
                match = next(
                    (item for item in serial_data_list if item.get("sr_no") == m.serial_number),
                    None
                )
                if not match:
                    continue

                # Parse coverage end date
                date_str = match.get("coverage_end_date")
                if date_str:
                    try:
                        m.warranty_expiry = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        m.warranty_expiry = None
                else:
                    m.warranty_expiry = None

                m.under_warranty = match.get("is_covered") == "YES"
                m.eox_announced = match.get("end_of_sale_date")
                m.eox_eol = match.get("end_of_support_date")

                updated_modules.append({
                    "module_id": m.id,
                    "serial_number": m.serial_number,
                    "updated": True,
                })

            except Exception as e:
                errors.append({
                    "module_id": m.id,
                    "serial_number": m.serial_number,
                    "error": str(e),
                })

        session.commit()

        update_job(
            job_id,
            status="completed",
            finished_at=datetime.now(timezone.utc),
            result={
                "updated_modules": updated_modules,
                "errors": errors,
            }
        )

    except Exception as e:
        session.rollback()
        update_job(
            job_id,
            status="failed",
            finished_at=datetime.now(timezone.utc),
            error=str(e),
        )
