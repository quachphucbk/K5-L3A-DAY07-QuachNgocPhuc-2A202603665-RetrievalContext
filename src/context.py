"""Pack whole chunks in rank order; budget is Python characters incl. sources."""


class NeighborIndex:
    """Đoạn kề theo offset, cùng tài liệu/trang/section và segment nguồn."""
    def __init__(self, chunks):
        groups = {}
        for chunk in chunks:
            m = chunk["metadata"]
            key = (chunk["source_id"], chunk["page"], m.get("section"), m.get("segment_start", 0))
            groups.setdefault(key, []).append(chunk)
        self.neighbors = {}
        for group in groups.values():
            group.sort(key=lambda c: (c["metadata"]["start"], c["id"]))
            for i, chunk in enumerate(group):
                self.neighbors[chunk["id"]] = group[max(0, i - 1):i] + group[i + 1:i + 2]

    def expand(self, results):
        # Mỗi anchor đi cùng hàng xóm ngay sau nó; không dùng gold chọn đoạn.
        expanded, seen = [], set()
        for chunk in results:
            for candidate in [chunk, *self.neighbors.get(chunk["id"], [])]:
                if candidate["id"] not in seen:
                    expanded.append(candidate)
                    seen.add(candidate["id"])
        return expanded


def pack_context(results, budget=800):
    if type(budget) is not int or budget < 1:
        raise ValueError("budget phải là số nguyên dương, đơn vị ký tự")
    blocks, kept, seen = [], [], set()
    for chunk in results:
        if chunk["id"] in seen:
            continue
        seen.add(chunk["id"])
        block = f"[{chunk['id']} | {chunk['source']} | page {chunk['page']}]\n{chunk['text']}"
        if len("\n\n".join(blocks + [block])) <= budget:
            blocks.append(block)
            kept.append(chunk)
    return "\n\n".join(blocks), kept
