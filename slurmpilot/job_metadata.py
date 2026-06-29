import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class JobMetadata:
    """Persisted metadata written to ``metadata.json`` at scheduling time."""

    jobname: str
    cluster: str
    date: str
    remote_path: str | None = None

    def to_json(self) -> str:
        d = {"jobname": self.jobname, "cluster": self.cluster, "date": self.date}
        if self.remote_path is not None:
            d["remote_path"] = self.remote_path
        return json.dumps(d)

    @classmethod
    def from_json(cls, s: str) -> "JobMetadata":
        data = json.loads(s)
        # Support legacy format: jobname nested inside job_creation_info
        if "jobname" not in data and "job_creation_info" in data:
            data["jobname"] = data["job_creation_info"]["jobname"]
        return cls(
            jobname=data["jobname"],
            cluster=data["cluster"],
            date=data["date"],
            remote_path=data.get("remote_path"),
        )


def _search_metadata_recursively(jobs_root: Path) -> list["JobMetadata"]:
    """Walk ``jobs_root``, stopping descent at any directory that contains ``metadata.json``.

    Only returns entries whose jobname matches the path relative to jobs_root (skips moved jobs).
    """
    results = []
    stack = [jobs_root]
    while stack:
        cur = stack.pop()
        candidate = cur / "metadata.json"
        if candidate.exists():
            try:
                jobmetadata = JobMetadata.from_json(candidate.read_text())
                # Skip moved jobs: relative path from jobs_root must match jobname
                if candidate.parent.relative_to(jobs_root) == Path(jobmetadata.jobname):
                    results.append(jobmetadata)
            except json.JSONDecodeError:
                print(f"Error while reading {candidate}")
            except (TypeError, KeyError):
                pass
        else:
            for child in cur.iterdir():
                if child.is_dir():
                    stack.append(child)
    return sorted(results, key=lambda m: m.date, reverse=True)


def list_metadatas(
    jobs_root: Path,
    n_jobs: int | None = None,
    clusters: list[str] | None = None,
) -> list["JobMetadata"]:
    """Return JobMetadata found under ``jobs_root``, sorted newest-first by creation date."""
    if not jobs_root.exists():
        return []
    results = _search_metadata_recursively(jobs_root)
    if clusters is not None:
        results = [m for m in results if m.cluster in clusters]
    if n_jobs is not None:
        results = results[:n_jobs]
    return results
