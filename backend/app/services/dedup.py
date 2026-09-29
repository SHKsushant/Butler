"""
Groups near-duplicate tickets (e.g. five people reporting the same
outage) into clusters, so the dashboard can show one issue instead of
five separate rows. Simple threshold-based clustering over cosine
similarity - no need for a heavier clustering algorithm at hackathon
scale (dozens to low hundreds of tickets).
"""
from typing import List
import math

from app.models import Ticket

SIMILARITY_THRESHOLD = 0.72  # tuned empirically on the sample dataset


def cluster_tickets(tickets: List[Ticket]) -> None:
    """Assigns `cluster_id` to each ticket in place. Tickets with no
    close match get their own singleton cluster (cluster_id = their own id)."""
    embedded = [t for t in tickets if t.get_embedding() is not None]
    if not embedded:
        return

    vectors = [t.get_embedding() for t in embedded]

    def cosine_similarity(left: List[float], right: List[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0

    n = len(embedded)
    # Similarity is transitive for an incident cluster: if A matches B and B
    # matches C, all three reports should be reviewed together.  Union-find
    # avoids the order-dependent grouping produced by a single forward pass.
    parent = list(range(n))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for i in range(n):
        for j in range(i + 1, n):
            if cosine_similarity(vectors[i], vectors[j]) >= SIMILARITY_THRESHOLD:
                union(i, j)

    cluster_numbers = {}
    assigned = []
    for i in range(n):
        root = find(i)
        if root not in cluster_numbers:
            cluster_numbers[root] = len(cluster_numbers) + 1
        assigned.append(cluster_numbers[root])

    for ticket, cluster_id in zip(embedded, assigned):
        ticket.cluster_id = cluster_id


def cluster_sizes(tickets: List[Ticket]) -> dict:
    """Returns {cluster_id: count} for annotating the API response."""
    sizes: dict = {}
    for t in tickets:
        if t.cluster_id is not None:
            sizes[t.cluster_id] = sizes.get(t.cluster_id, 0) + 1
    return sizes
