from app.domain.models import StorageNode
from app.storage.cluster import ConsistentHashRing


def test_ring_returns_unique_healthy_nodes():
    nodes = [StorageNode(f"node-{i}") for i in range(1, 6)]
    ring = ConsistentHashRing(nodes, virtual_nodes=5)
    selected = ring.get_nodes("chunk-1", 2)
    assert len(selected) == 2
    assert len({node.node_id for node in selected}) == 2


def test_ring_skips_unhealthy_nodes():
    nodes = [StorageNode(f"node-{i}") for i in range(1, 4)]
    nodes[0].healthy = False
    ring = ConsistentHashRing(nodes, virtual_nodes=5)
    selected = ring.get_nodes("chunk-1", 3)
    assert all(node.healthy for node in selected)
