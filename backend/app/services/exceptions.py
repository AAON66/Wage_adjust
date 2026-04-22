from __future__ import annotations


class TierRecomputeBusyError(Exception):
    """Phase 34 D-05/D-06：另一个事务持有该 year 的 snapshot 行锁（FOR UPDATE NOWAIT 失败）。

    API 层 catch → 409 Conflict + retry_after_seconds=5。
    """

    def __init__(self, year: int, message: str | None = None) -> None:
        self.year = year
        super().__init__(message or f'Tier recompute busy for year {year}')


class TierRecomputeFailedError(Exception):
    """Phase 34 D-04：重算执行失败（Engine 异常 / 数据库写入失败）。

    Service 层不阻塞调用方（import 落库已成功，旧快照保留）；上层根据需要决定是
    422（手动调 recompute）还是 silently log（import 自动重算路径）。
    """

    def __init__(self, year: int, cause: str) -> None:
        self.year = year
        self.cause = cause
        super().__init__(f'Tier recompute failed for year {year}: {cause}')
