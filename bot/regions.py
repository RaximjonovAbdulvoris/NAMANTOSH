"""Regional routing. Missing destinations never fall back to another branch."""
import os

from bot.config import ARCHIVE_GROUP, BRAND_GROUP, DRIVER_GROUPS

NAMANGAN = "namangan"
TASHKENT = "tashkent"
REGION_NAMES = {NAMANGAN: "WB HUMO Namangan", TASHKENT: "WB HUMO Toshkent"}


def get_region(context) -> str | None:
    region = context.user_data.get("region")
    return region if region in REGION_NAMES else None


def region_name(region: str) -> str:
    return REGION_NAMES[region]


def clear_application(context) -> None:
    region = get_region(context)
    context.user_data.clear()
    if region:
        context.user_data["region"] = region


def driver_groups(region: str) -> list[str]:
    if region == NAMANGAN:
        return [group for group in DRIVER_GROUPS if group]
    if region == TASHKENT:
        return [value for i in (1, 2)
                if (value := os.environ.get(f"TASHKENT_DRIVER_GROUP_{i}", "").strip())]
    return []


def application_group(region: str, kind: str) -> str:
    if region == NAMANGAN and kind == "brand":
        return BRAND_GROUP
    if region == TASHKENT and kind in ("brand", "spectre"):
        key = "TASHKENT_BRAND_GROUP" if kind == "brand" else "TASHKENT_SPECTRE_GROUP"
        return os.environ.get(key, "").strip()
    return ""


def archive_group(region: str) -> str:
    if region == NAMANGAN:
        return ARCHIVE_GROUP
    if region == TASHKENT:
        return os.environ.get("TASHKENT_ARCHIVE_GROUP", "").strip()
    return ""