# Verilog Netlist Parser - ee24s053 Karthik B K - March 13 2025
import re, sys
from collections import defaultdict

class DAG:
    def __init__(self):
        self.graph = {}

    def add_node(self, node):
        if node not in self.graph:
            self.graph[node] = set(); return True
        return False

    def add_edge(self, src, dst):
        for node in [src, dst]:
            if node not in self.graph:
                self.graph[node] = set()
        if self._would_create_cycle(src, dst):
            raise ValueError(f"Edge {src}->{dst} would create cycle")
        self.graph[src].add(dst); return True

    def _would_create_cycle(self, src, dst):
        return self._can_reach(dst, src)

    def _can_reach(self, start, end, visited=None):
        if visited is None: visited = set()
        if start == end: return True
        visited.add(start)
        for neighbor in self.graph.get(start, set()):
            if neighbor not in visited and self._can_reach(neighbor, end, visited): return True
        return False

    def get_children(self, node):
        if node not in self.graph: raise KeyError(f"Node {node} not in graph")
        return self.graph[node].copy()

    def get_parents(self, node):
        if node not in self.graph: raise KeyError(f"Node {node} not in graph")
        return {n for n in self.graph if node in self.graph[n]}

    def get_descendants(self, node):
        if node not in self.graph: raise KeyError(f"Node {node} not in graph")
        result = set(); self._collect_descendants(node, result); return result

    def _collect_descendants(self, node, result):
        for child in self.graph[node]:
            if child not in result: result.add(child); self._collect_descendants(child, result)

    def get_ancestors(self, node):
        if node not in self.graph: raise KeyError(f"Node {node} not in graph")
        result = set(); self._collect_ancestors(node, result); return result

    def _collect_ancestors(self, node, result):
        for parent in self.get_parents(node):
            if parent not in result: result.add(parent); self._collect_ancestors(parent, result)

    def topological_sort(self):
        in_degree = {node: 0 for node in self.graph}
        for node in self.graph:
            for child in self.graph[node]: in_degree[child] = in_degree.get(child, 0) + 1
        queue = [node for node in self.graph if in_degree[node] == 0]; result = []
        while queue:
            node = queue.pop(0); result.append(node)
            for child in self.graph[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0: queue.append(child)
        if len(result) != len(self.graph): raise ValueError("Graph contains a cycle")
        return result

    def is_acyclic(self):
        try: self.topological_sort(); return True
        except ValueError: return False

    def remove_edge(self, src, dst):
        if src not in self.graph or dst not in self.graph: return False
        if dst in self.graph[src]: self.graph[src].remove(dst); return True
        return False

    def remove_node(self, node):
        if node not in self.graph: return False
        del self.graph[node]
        for src in self.graph:
            if node in self.graph[src]: self.graph[src].remove(node)
        return True

    def __str__(self):
        result = ["DAG:"]
        for node in sorted(self.graph, key=str):
            children = sorted(self.graph[node], key=str)
            result.append(f"{node} -> {', '.join(map(str, children))}" if children else f"{node}")
        return "\n".join(result)

    def __len__(self):
        return len(self.graph)

    def __contains__(self, node):
        return node in self.graph

class VerilogParser:
    def __init__(self, filename):
        self.filename = filename
        self.dag = DAG()
        self.inputs = []
        self.outputs = []
        self.gates = {}
        self.fanouts = defaultdict(list)
        self.gate_depths = {}
        self.max_depth_path = []
    
    def parse(self):
        with open(self.filename, 'r') as f:
            content = f.read()
        # Extract inputs/outputs
        input_match = re.search(r'input\s+([^;]+);', content)
        if input_match:
            self.inputs = [x.strip() for x in input_match.group(1).replace('\n', '').split(',')]
        output_match = re.search(r'output\s+([^;]+);', content)
        if output_match:
            self.outputs = [x.strip() for x in output_match.group(1).replace('\n', '').split(',')]
        # Extract gates
        for match in re.finditer(r'(not|nand|nor)\s+(\w+)\s+\(([^)]+)\);', content):
            gate_type, gate_name = match.group(1), match.group(2)
            pins = [x.strip() for x in match.group(3).split(',')]
            output_pin, input_pins = pins[0], pins[1:]
            # Store gate info
            self.gates[gate_name] = {'type': gate_type, 'output': output_pin, 'inputs': input_pins}
            # Add to DAG
            self.dag.add_node(output_pin)
            for input_pin in input_pins:
                self.dag.add_node(input_pin)
                self.dag.add_edge(input_pin, output_pin)
        # Add primary I/O
        for pin in self.inputs + self.outputs:
            self.dag.add_node(pin)
            
        # Calculate fanouts after all gates are processed
        for gate_name, gate_info in self.gates.items():
            for input_pin in gate_info['inputs']:
                # Find which gate this input comes from
                for src_gate, src_info in self.gates.items():
                    if src_info['output'] == input_pin:
                        self.fanouts[src_gate].append(gate_name)
    
    def calculate_gate_depths(self):
        self.gate_depths = {}
        # Set depth 0 for inputs
        for input_pin in self.inputs: self.gate_depths[input_pin] = 0
        # Process in topological order
        try: topo_order = self.dag.topological_sort()
        except ValueError:
            print("Error: Circuit contains a cycle, which is not expected in a combinational circuit")
            return
        for node in topo_order:
            if node in self.inputs: continue
            parents = self.dag.get_parents(node)
            if parents:
                max_parent_depth = max(self.gate_depths.get(parent, 0) for parent in parents)
                self.gate_depths[node] = max_parent_depth + 1
            else: self.gate_depths[node] = 0
    
    def find_longest_path(self):
        self.calculate_gate_depths()
        # Find deepest output
        max_depth, deepest_output = 0, None
        for output_pin in self.outputs:
            depth = self.gate_depths.get(output_pin, 0)
            if depth > max_depth: max_depth, deepest_output = depth, output_pin
        if not deepest_output: return []
        # Trace back from output
        path, current = [deepest_output], deepest_output
        while self.gate_depths.get(current, 0) > 0:
            parents = self.dag.get_parents(current)
            if not parents: break
            # Find parent with max depth
            max_parent_depth, max_parent = 0, None
            for parent in parents:
                parent_depth = self.gate_depths.get(parent, 0)
                if parent_depth > max_parent_depth: max_parent_depth, max_parent = parent_depth, parent
            if max_parent: path.append(max_parent); current = max_parent
            else: break
        self.max_depth_path = list(reversed(path))
        return self.max_depth_path
    
    def print_fanouts(self):
        print("\nFanout information:")
        for gate_name in sorted(self.gates.keys()):
            fanout_str = ", ".join(self.fanouts[gate_name]) if gate_name in self.fanouts and self.fanouts[gate_name] else "No fanouts"
            print(f"{gate_name} - {fanout_str}")
    
    def print_longest_path(self):
        if not self.max_depth_path: self.find_longest_path()
        print("\nLongest path information:")
        print(f"Path length (logic depth): {len(self.max_depth_path) - 1}")
        print(f"Path: {' -> '.join(self.max_depth_path)}")
        # Find gates in path
        gates_in_path = []
        for i in range(len(self.max_depth_path) - 1):
            current, next_node = self.max_depth_path[i], self.max_depth_path[i + 1]
            for gate_name, gate_info in self.gates.items():
                if gate_info['output'] == next_node: gates_in_path.append(gate_name); break
        if gates_in_path: print(f"Gates in path: {' -> '.join(gates_in_path)}")

def main():
    if len(sys.argv) != 2: print("Usage: python parser.py <verilog_file>"); return
    parser = VerilogParser(sys.argv[1])
    parser.parse()
    parser.find_longest_path()
    parser.print_longest_path()
    # parser.print_fanouts()

if __name__ == "__main__": main()
