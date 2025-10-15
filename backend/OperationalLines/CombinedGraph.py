import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from LineData.BlueLine import blue_line
from LineData.GreenLine import green_line
from LineData.OrangeLine import orange_line
from LineData.PurpleLine import purple_line
from LineData.YellowLine import yellow_line

# Combine all line dictionaries
lines = [blue_line, green_line, orange_line, purple_line, yellow_line]

# Build adjacency list without overwriting
metro_graph = {}

for line in lines:
    stations = list(line.keys())
    for i, station in enumerate(stations):
        if station not in metro_graph:
            metro_graph[station] = set()
        # Add neighbors
        if i > 0:
            metro_graph[station].add(stations[i-1])
        if i < len(stations) - 1:
            metro_graph[station].add(stations[i+1])

# Convert sets to sorted lists
for station in metro_graph:
    metro_graph[station] = sorted(list(metro_graph[station]))

if __name__ == "__main__":
    for station, neighbors in metro_graph.items():
        print(f"{station}: {neighbors}")
