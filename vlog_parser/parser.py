#############################################################
# Author: ee24s053 Karthik B K
# Date: 20 March 2025
#
# This code is heavily modified by c3.7s+t
# This file does not have any commenting for the same reason.
#############################################################

import datetime
import re, sys
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# this structure is used for lingest path search.
from collections import deque

class Gate:
    def __init__(self, name, gate_type):
        self.name = name
        self.gate_type = gate_type
        self.inputs = []
        self.outputs = []
        self.pi_inputs = []
        self.po_outputs = []
        self.input_mapping = {}
        # Store the original Verilog input ports order
        self.verilog_inputs = []
    
    def add_input(self, gate):
        if isinstance(gate, Gate) and gate not in self.inputs:
            self.inputs.append(gate)
            if self not in gate.outputs: gate.outputs.append(self)
    
    def add_output(self, gate):
        if isinstance(gate, Gate) and gate not in self.outputs:
            self.outputs.append(gate)
            if self not in gate.inputs: gate.inputs.append(self)
            
    def add_pi_input(self, pi_name):
        if pi_name not in self.pi_inputs:
            self.pi_inputs.append(pi_name)
    
    def add_po_output(self, po_name):
        if po_name not in self.po_outputs:
            self.po_outputs.append(po_name)

    def __repr__(self) -> str:
        input_names = [inp.name for inp in self.inputs]
        all_inputs = input_names + self.pi_inputs
        
        output_names = [out.name for out in self.outputs]
        all_outputs = output_names + self.po_outputs
        
        mapping_str = ', mapping=' + str(self.input_mapping) if self.input_mapping else ''
                
        return f'Gate({self.name}, type={self.gate_type}, inputs={all_inputs}, outputs={all_outputs}{mapping_str})'

class Net:
    def __init__(self, name, source=None, destinations=None):
        self.name, self.source, self.destinations, self.value = name, source, destinations or [], None
    
    def add_destination(self, gate):
        if gate not in self.destinations: self.destinations.append(gate)
    
    def set_source(self, gate):
        self.source = gate

class Circuit:
    def __init__(self):
        self.gates, self.nets, self.inputs, self.outputs = {}, {}, [], []
        self.gate_order = []
        
    def visualize_dag(self, output_file=None):
        G = nx.DiGraph()
        for gate_name, gate in self.gates.items():
            G.add_node(gate_name, type=gate.gate_type)
        for gate_name, gate in self.gates.items():
            for output_gate in gate.outputs:
                G.add_edge(gate_name, output_gate.name)
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, seed=42)
        nx.draw_networkx_nodes(G, pos, node_size=700, node_color='lightblue')
        nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle='->', arrowsize=15)
        nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif')
        plt.title('Circuit DAG Visualization', fontsize=15)
        plt.axis('off')
        if output_file:
            plt.savefig(output_file, format='png', dpi=300, bbox_inches='tight')
            plt.close()
            return output_file
        else:
            plt.tight_layout()
            plt.show()
            return None
    
    def add_gate(self, gate):
        self.gates[gate.name] = gate
        if gate.name not in self.gate_order:
            self.gate_order.append(gate.name)
    
    def add_net(self, net): self.nets[net.name] = net
    
    def connect(self, source_gate_name, dest_gate_name, net_name=None):
        source_gate, dest_gate = self.gates.get(source_gate_name), self.gates.get(dest_gate_name)
        if not source_gate or not dest_gate: raise ValueError(f"Cannot connect: gate not found")
        
        net_name = net_name or f"{source_gate_name}_to_{dest_gate_name}"
        if net_name not in self.nets:
            net = Net(net_name, source_gate, [dest_gate])
            self.add_net(net)
        else:
            net = self.nets[net_name]
            net.set_source(source_gate)
            net.add_destination(dest_gate)
        
        source_gate.add_output(dest_gate)
        dest_gate.add_input(source_gate)
        
        for i, input_gate in enumerate(dest_gate.inputs):
            if input_gate.name == source_gate.name:
                dest_gate.input_mapping[i] = source_gate.name
                break
        
        return net
    
    def set_input_gates(self, gate_names): self.inputs = gate_names
    
    def set_output_gates(self, gate_names): self.outputs = gate_names
    
    def get_fanouts(self):
        return {gate_name: [g.name for g in gate.outputs] for gate_name, gate in self.gates.items()}
    
    def get_one_longest_path(self):
        # make an adjacency list. for each vertex, note what vertices are connected ot it.
        adj = {name: [g.name for g in gate.outputs] for name, gate in self.gates.items()}

        # initilaize in-degree to zero for all vertices.
        # this is basically going to conunt how many edges are coming _into_ that node.
        # this is used within the topp sirt algorithm.
        in_deg = {name: 0 for name in self.gates}
        for outs in adj.values():
            for v in outs:
                in_deg[v] += 1
        # topo sort. for every edge u ~> v, u must come before v in the ordering.
        # this is needed to ensure inputs are handled before the gagte itself.
        topo = []
        q = deque([n for n, d in in_deg.items() if d == 0])
        while q:
            u = q.popleft()
            topo.append(u)
            for v in adj[u]:
                in_deg[v] -= 1
                if in_deg[v] == 0:
                    q.append(v)
        # search for longest path using topo sort. this is basically foing to be linear time O(v+e)
        dist = {n: 1 for n in self.gates}  # node count
        parent = {n: None for n in self.gates}
        for u in topo:
            for v in adj[u]:
                # if the longest path going to v so far is shorter than the path going through u, update
                if dist[v] < dist[u] + 1:
                    dist[v] = dist[u] + 1
                    parent[v] = u
        # Find sink with max dist - this is going to be the longest path.
        sinks = [gn for gn, g in self.gates.items() if not g.outputs]
        if not sinks:
            # this should'nt happen foe the iscas85 benches.
            return [], 0
        end = max(sinks, key=lambda n: dist[n])
        max_length = dist[end]
        # Reconstruct longest path. backwards and then reverse it.
        path = []
        while end is not None:
            path.append(end)
            end = parent[end]
        path.reverse()
        return path, max_length

def parse(file_contents):
    circuit = Circuit()
    patterns = {
        'input': re.compile(r'input\s+([^;]+);'),
        'output': re.compile(r'output\s+([^;]+);'),
        'wire': re.compile(r'wire\s+([^;]+);'),
        'gate': re.compile(r'(not|nand|nor)\s+(\w+)\s*\(([^)]+)\);', re.MULTILINE)
    }
    
    inputs = [inp.strip() for inp in patterns['input'].search(file_contents).group(1).split(',')] if patterns['input'].search(file_contents) else []
    outputs = [out.strip() for out in patterns['output'].search(file_contents).group(1).split(',')] if patterns['output'].search(file_contents) else []
    wires = [wire.strip() for wire in patterns['wire'].search(file_contents).group(1).split(',')] if patterns['wire'].search(file_contents) else []
    
    for signal_name in inputs + outputs + wires: circuit.add_net(Net(signal_name))
    
    for gate_match in patterns['gate'].finditer(file_contents):
        gate_type, gate_name = gate_match.group(1).upper(), gate_match.group(2)
        if not any(gate_name.lower().startswith(prefix) for prefix in ['nand', 'nor', 'not']): continue
            
        ports = [port.strip() for port in gate_match.group(3).split(',')]
        output_port, input_ports = ports[0], ports[1:]
        
        gate = Gate(gate_name, gate_type)
        circuit.add_gate(gate)
        
        output_net = circuit.nets.get(output_port) or Net(output_port)
        if output_port not in circuit.nets: circuit.add_net(output_net)
        output_net.set_source(gate)
        
        gate.verilog_inputs = input_ports.copy()
        
        for i, input_port in enumerate(input_ports):
            input_net = circuit.nets.get(input_port) or Net(input_port)
            if input_port not in circuit.nets: circuit.add_net(input_net)
            input_net.add_destination(gate)
            
            if input_port in inputs:
                pi_name = f"PI_{input_port}"
                gate.add_pi_input(pi_name)
                gate.input_mapping[i] = pi_name
            else:
                gate.input_mapping[i] = input_port
        
        if output_port in outputs:
            po_name = f"PO_{output_port}"
            gate.add_po_output(po_name)

    for net_name, net in circuit.nets.items():
        if net.source and net.destinations:
            source_gate = net.source
            for dest_gate in net.destinations:
                if source_gate.name != dest_gate.name:
                    is_gate = lambda g: any(g.name.lower().startswith(p) for p in ['nand', 'nor', 'not'])
                    if is_gate(source_gate) and is_gate(dest_gate): circuit.connect(source_gate.name, dest_gate.name, net_name)
    
    # we make a mapping for ech gate, as to what input is connected to what pin
    # this makes constraint-gen a whole lot easier. otherwise it is a pain to get
    # the constraints right when solving for gate sizing. this is the right place
    # to do it because then the solver setup is clean - just have to access this var.
    for gate_name, gate in circuit.gates.items():
        new_mapping = {}
        
        for i, verilog_input in enumerate(gate.verilog_inputs):
            if verilog_input in inputs:
                new_mapping[i] = f'PI_{verilog_input}'
            else:
                if verilog_input in circuit.nets and circuit.nets[verilog_input].source:
                    new_mapping[i] = circuit.nets[verilog_input].source.name
                else:
                    new_mapping[i] = verilog_input
        
        gate.input_mapping = new_mapping
    
    circuit.set_input_gates(inputs)
    circuit.set_output_gates(outputs)
    return circuit

def analyze_circuit(ckt):
    print(f"This file is automatically generated by Karthik's verilog parser on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nCircuit Analysis:\n=================")
    
    print("\nGates and Fanouts:")
    print("----------------")
    def get_gate_number(gate_name):
        try:
            parts = gate_name.split('_')
            if len(parts) < 2:
                return float('inf')
                
            num_part = parts[1]
            return int(num_part)
        except (IndexError, ValueError):
            return float('inf')
    
    fanouts = ckt.get_fanouts()
    for gate_name in sorted(fanouts.keys(), key=get_gate_number):
        gate_fanouts = fanouts[gate_name]
        print(f"Gate: {gate_name}\tFanouts: {', '.join(sorted(gate_fanouts, key=get_gate_number)) if gate_fanouts else 'None'}")

    print("\nLongest Path:")
    print("-------------")
    path, max_length = ckt.get_one_longest_path()
    if path:
        print(f"  Maximum path length: {max_length} nodes")
        print("    ", " -> ".join(path))
    else:
        print("  No path found.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Error: Please provide a netlist file as an argument")
        sys.exit(1)
    
    try:
        with open(sys.argv[1], 'r') as f: file_contents = f.read()
        circuit = parse(file_contents)
        
        base_filename = sys.argv[1].split('.')[0]
        output_file = f"{base_filename}_dag.png"
        
        # try:
        #     circuit.visualize_dag(output_file)
        #     print(f"DAG visualization saved to: {output_file}")
        # except:
        #     pass
        
        analyze_circuit(circuit)
    except FileNotFoundError: print(f"Error: File '{sys.argv[1]}' not found"); sys.exit(1)
    except Exception as e: print(f"Error: {e}"); sys.exit(1)