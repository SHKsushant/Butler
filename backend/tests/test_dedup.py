from app.models import Ticket
from app.services.dedup import cluster_tickets, cluster_sizes


def make_ticket(id_, vec):
    t = Ticket(id=id_, sender_email="a@example.com", subject="s", body="b")
    t.set_embedding(vec)
    return t


def test_near_identical_vectors_cluster_together():
    tickets = [
        make_ticket(1, [1.0, 0.0, 0.0]),
        make_ticket(2, [0.99, 0.01, 0.0]),  # nearly identical direction
        make_ticket(3, [0.0, 1.0, 0.0]),    # orthogonal - unrelated
    ]
    cluster_tickets(tickets)
    assert tickets[0].cluster_id == tickets[1].cluster_id
    assert tickets[0].cluster_id != tickets[2].cluster_id


def test_every_ticket_gets_a_cluster_id():
    tickets = [make_ticket(i, [float(i), 0.0, 0.0]) for i in range(1, 5)]
    cluster_tickets(tickets)
    assert all(t.cluster_id is not None for t in tickets)


def test_cluster_sizes_counts_correctly():
    tickets = [
        make_ticket(1, [1.0, 0.0]),
        make_ticket(2, [1.0, 0.0]),
        make_ticket(3, [1.0, 0.0]),
        make_ticket(4, [-1.0, 0.0]),
    ]
    cluster_tickets(tickets)
    sizes = cluster_sizes(tickets)
    # the three identical vectors should share one cluster of size 3
    assert 3 in sizes.values()


def test_empty_list_does_not_crash():
    cluster_tickets([])  # should simply do nothing
    assert cluster_sizes([]) == {}


def test_tickets_without_embeddings_are_left_alone():
    t = Ticket(id=1, sender_email="a@example.com", subject="s", body="b")
    cluster_tickets([t])
    assert t.cluster_id is None
