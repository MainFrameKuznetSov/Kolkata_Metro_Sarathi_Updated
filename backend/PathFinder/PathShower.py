# backend/PathFinder/PathFinder.py
import sys
import heapq
import re
from pathlib import Path
from collections import defaultdict, Counter

# allow running from PathFinder folder directly
project_root = Path(__file__).resolve().parents[2]  # repo root -> backend
sys.path.append(str(project_root / "backend"))

# --- Import line dicts (explicit, matches your CombinedGraph.py imports) ---
try:
    from LineData.BlueLine import blue_line
    from LineData.GreenLine import green_line
    from LineData.OrangeLine import orange_line
    from LineData.PurpleLine import purple_line
    from LineData.YellowLine import yellow_line
except Exception as e:
    print("Error importing line files from backend/LineData:", e)
    raise

LINE_ITEMS = [
    ("BlueLine", blue_line),
    ("GreenLine", green_line),
    ("OrangeLine", orange_line),
    ("PurpleLine", purple_line),
    ("YellowLine", yellow_line),
]

# ---------- Utilities ----------
def normalize_name(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def find_station_by_display(query: str, canonical_to_display: dict):
    # exact match
    for cid, display in canonical_to_display.items():
        if display == query:
            return cid
    # normalized fallback
    nq = normalize_name(query)
    for cid, display in canonical_to_display.items():
        if normalize_name(display) == nq:
            return cid
    return None

# ---------- Build graph with line info ----------
def build_graph_and_station_lines(line_items):
    """
    graph: dict[station] -> dict[neighbor_station] -> set(line_names)
    station_lines: dict[station] -> set(line_names)
    canonical_to_display: dict[station] -> representative display name (string)
    id_to_names: dict[station] -> Counter(display_names)  (for warnings)
    """
    graph = defaultdict(lambda: defaultdict(set))
    station_lines = defaultdict(set)
    id_to_names = defaultdict(Counter)

    # We'll use the raw station names as canonical keys (you said you fixed inconsistent spellings)
    # If you prefer ID-based canonicalization, we can change to use detect_station_id used earlier.
    for line_name, line_dict in line_items:
        stations = list(line_dict.keys())
        for s in stations:
            id_to_names[s][s] += 1
            station_lines[s].add(line_name)
        for i in range(len(stations) - 1):
            a, b = stations[i], stations[i + 1]
            graph[a][b].add(line_name)
            graph[b][a].add(line_name)

    canonical_to_display = {s: s for s in id_to_names.keys()}
    return graph, station_lines, canonical_to_display, id_to_names

# ---------- Dijkstra-like search minimizing (switches, stations) ----------
def find_min_switch_path(graph, station_lines, src, dest):
    """
    Returns (path_list_of_stations, switches, stations_traversed, lines_used_along_path)
    or (None, None, None, None) if no path.
    """
    if src not in station_lines or dest not in station_lines:
        return None, None, None, None

    pq = []
    visited = {}  # visited[(station, line)] = (best_switches, best_stations)

    # initialize: one entry per line that source belongs to
    for line in station_lines[src]:
        heapq.heappush(pq, (0, 0, src, line, None))
        visited[(src, line)] = (0, 1)

    best_final = None

    while pq:
        switches, stations_count, curr, curr_line, parent = heapq.heappop(pq)

        # stale state check
        if visited.get((curr, curr_line), (float("inf"), float("inf"))) < (switches, stations_count):
            continue

        if curr == dest:
            best_final = (switches, stations_count, curr, curr_line, parent)
            break

        for nbr, lines_between in graph[curr].items():
            # prefer staying on curr_line if available, else pick deterministic fallback
            if curr_line in lines_between:
                edge_line = curr_line
            else:
                edge_line = min(lines_between)

            new_switches = switches + (edge_line != curr_line)
            new_stations = stations_count + 1

            key = (nbr, edge_line)
            best_seen = visited.get(key, (float("inf"), float("inf")))

            if (new_switches, new_stations) < best_seen:
                visited[key] = (new_switches, new_stations)
                heapq.heappush(pq, (new_switches, new_stations, nbr, edge_line,
                                     (switches, stations_count, curr, curr_line, parent)))

    if best_final is None:
        return None, None, None, None

    # reconstruct path and lines used
    switches, stations_count, station, line_used_at_station, parent = best_final
    rev_stations = [station]
    rev_lines = [line_used_at_station]  # line used to arrive at 'station'
    ptr = parent
    while ptr is not None:
        _, _, prev_station, prev_line, prev_parent = ptr
        rev_stations.append(prev_station)
        rev_lines.append(prev_line)  # line used to arrive at prev_station
        ptr = prev_parent

    rev_stations.reverse()
    rev_lines.reverse()
    # rev_lines[i] is the line used to be "on" at station i (initial line for source is rev_lines[0])
    # The line used to travel the edge station[i] -> station[i+1] is rev_lines[i+1]
    lines_for_edges = []
    for i in range(len(rev_stations) - 1):
        lines_for_edges.append(rev_lines[i + 1])

    return rev_stations, switches, stations_count, lines_for_edges

# ---------- CLI ----------
def main():
    graph, station_lines, canonical_to_display, id_to_names = build_graph_and_station_lines(LINE_ITEMS)

    # warn inconsistent names (unlikely since you fixed them)
    for s, counter in id_to_names.items():
        if len(counter) > 1:
            print(f"WARNING: station key '{s}' has multiple display forms: {dict(counter)}")

    src_q = input("Source station: ").strip()
    dest_q = input("Destination station: ").strip()

    # try direct matches then normalized
    src = find_station_by_display(src_q, canonical_to_display)
    dest = find_station_by_display(dest_q, canonical_to_display)

    if src is None:
        print("Source not found. Try exact name or normalized form.")
        return
    if dest is None:
        print("Destination not found. Try exact name or normalized form.")
        return

    path, switches, stations_traversed, lines_for_edges = find_min_switch_path(graph, station_lines, src, dest)
    if path is None:
        print("No path found between the stations.")
        return

    print("\nPath (stations):")
    print(" -> ".join(path))
    print(f"Stations traversed (including source): {stations_traversed}")
    print(f"Number of switches: {switches}")

    # print("\nLegs (station_a -> station_b) with line used:")
    # for i in range(len(path) - 1):
    #     print(f"{path[i]} -> {path[i+1]}   (Line used: {lines_for_edges[i]})")

if __name__ == "__main__":
    main()
