from db_handler.services.outbox_processor import process_outbox

def register_outbox_scheduler(scheduler) -> None:
    scheduler.add_job(
        process_outbox,
        "interval",
        id="process_outbox",
        seconds=15,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
