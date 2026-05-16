from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.data_sources.manager import datasource_manager


class DataProvenance:
    def __init__(
        self,
        source: str,
        fetched_at: Optional[str] = None,
        data_date: Optional[str] = None,
        lag_days: Optional[int] = None,
        is_estimated: bool = False,
        estimation_note: Optional[str] = None
    ):
        self.source = source
        self.fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
        self.data_date = data_date
        self.lag_days = lag_days
        self.is_estimated = is_estimated
        self.estimation_note = estimation_note

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "source": self.source,
            "fetched_at": self.fetched_at,
        }
        if self.data_date:
            result["data_date"] = self.data_date
        if self.lag_days is not None:
            result["lag_days"] = self.lag_days
        if self.is_estimated:
            result["is_estimated"] = True
            result["estimation_note"] = self.estimation_note
        return result


def annotate_data_source(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    source_name = datasource_manager.current_source_name or "unknown"
    provenance = DataProvenance(source=source_name)
    data["_provenance"] = provenance.to_dict()
    data["_data_type"] = data_type
    return data


def annotate_estimated_data(
    data: Dict[str, Any],
    data_type: str,
    estimation_note: str
) -> Dict[str, Any]:
    source_name = datasource_manager.current_source_name or "estimated"
    provenance = DataProvenance(
        source=source_name,
        is_estimated=True,
        estimation_note=estimation_note
    )
    data["_provenance"] = provenance.to_dict()
    data["_data_type"] = data_type
    return data


def annotate_stale_data(
    data: Dict[str, Any],
    data_type: str,
    data_date: str,
    lag_days: int
) -> Dict[str, Any]:
    source_name = datasource_manager.current_source_name or "unknown"
    provenance = DataProvenance(
        source=source_name,
        data_date=data_date,
        lag_days=lag_days
    )
    data["_provenance"] = provenance.to_dict()
    data["_data_type"] = data_type
    return data
