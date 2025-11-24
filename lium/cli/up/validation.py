"""Up command validation."""


def validate(executor_id: str | None, gpu: str | None, count: int | None, country: str | None, ttl: str | None, until: str | None) -> tuple[bool, str]:
    """Validate up command inputs."""
    if executor_id and (gpu or country):
        return False, "Cannot use filters (--gpu, --country) when specifying an executor ID"

    if not executor_id and not (gpu or count or country):
        return False, "Must provide either EXECUTOR_ID or filters (--gpu, --count, --country)"

    if ttl and until:
        return False, "Cannot specify both --ttl and --until"

    return True, ""
