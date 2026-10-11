#!/usr/bin/env python3
"""Git-owned demonstration code. Shell never generates this file."""
def summarize(values: list[int]) -> dict[str, object]:
    if not values:
        raise ValueError("values cannot be empty")
    return {"count": len(values), "total": sum(values), "squares": [v * v for v in values]}

if __name__ == "__main__":
    print(summarize([3, 5, 8, 13, 21]))
