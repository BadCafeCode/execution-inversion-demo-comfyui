from comfy_execution.graph_utils import GraphBuilder, is_link
from comfy_execution.graph import ExecutionBlocker
from .tools import VariantSupport
from comfy_execution.node_utils import type_intersection
from typing import Dict, List
import re

class VariadicFlowNode:
    @classmethod
    def INPUT_TYPES(cls):
        raise NotImplementedError("INPUT_TYPES must be implemented by subclasses")

    @classmethod
    def get_max_index(cls, strs):
        current_max = -1
        for s in strs:
            # Find the first string of digits using a regex
            match = re.search(r"\d+", s)
            if match is not None:
                current_max = max(current_max, int(match.group(0)))
        return current_max

    @classmethod
    def resolve_dynamic_flow_types(
        cls,
        base_output_types: List[str],
        base_output_names: List[str],
        variadic_start_index: int,
        input_types: Dict[str, str],
        output_types: Dict[str, List[str]],
        entangled_types: Dict[str, Dict],
    ):
        num_entries = max(cls.get_max_index(input_types.keys()), cls.get_max_index(output_types.keys())) + 1
        for linked in entangled_types.get("flow_control", []):
            num_entries = max(
                num_entries,
                cls.get_max_index(linked['input_types']),
                cls.get_max_index(linked['output_types'])
            )
        num_sockets = num_entries + 1
        inputs = cls.INPUT_TYPES()
        outputs = base_output_types
        output_names = base_output_names
        for i in range(variadic_start_index, num_sockets):
            socket_type = "*"
            input_name = f"initial_value{i}"
            output_name = f"value{i}"
            socket_type = type_intersection(socket_type, input_types.get(input_name, "*"))
            for output_type in output_types.get(output_name, []):
                socket_type = type_intersection(socket_type, output_type)
            for linked in entangled_types.get("flow_control", []):
                socket_type = type_intersection(socket_type, linked['input_types'].get(input_name, "*"))
            inputs["optional"]["initial_value%d" % i] = (socket_type, {
                "forceInput": True,
                "displayOrder": i,
                "rawLink": True,
            })
            outputs.append(socket_type)
            output_names.append(output_name)
        return {
            "input": inputs,
            "output": tuple(outputs),
            "output_name": tuple(output_names)
        }

NUM_FLOW_SOCKETS = 2
@VariantSupport()
class WhileLoopOpen(VariadicFlowNode):
    @classmethod
    def resolve_dynamic_types(cls, input_types, output_types, entangled_types):
        return cls.resolve_dynamic_flow_types(
            ['FLOW_CONTROL'],
            ['FLOW_CONTROL'],
            0,
            input_types,
            output_types,
            entangled_types,
        )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "condition": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "initial_value0": ("*",{"forceInput": True}),
            },
            "hidden": {
                "node_def": "NODE_DEFINITION",
            },
        }

    RETURN_TYPES = ("FLOW_CONTROL", "*")
    RETURN_NAMES = ("FLOW_CONTROL", "value0")
    FUNCTION = "while_loop_open"

    CATEGORY = "InversionDemo Nodes/Flow"

    def while_loop_open(self, condition, node_def=None, **kwargs):
        num_inputs = len(node_def['output'])
        values = []
        for i in range(num_inputs):
            values.append(kwargs.get("initial_value%d" % i, None))
        return tuple(["stub"] + values)

@VariantSupport()
class WhileLoopClose(VariadicFlowNode):
    @classmethod
    def resolve_dynamic_types(cls, input_types, output_types, entangled_types):
        return cls.resolve_dynamic_flow_types(
            [],
            [],
            0,
            input_types,
            output_types,
            entangled_types,
        )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "flow_control": ("FLOW_CONTROL", {
                    "rawLink": True,
                    "entangleTypes": True,
                    "displayOrder": -1,
                }),
                "condition": ("BOOLEAN", {
                    "forceInput": True,
                    "displayOrder": 999999,
                }),
            },
            "optional": {
                "initial_value0": ("*",{
                    "forceInput": True,
                    "rawLink": True,
                }),
            },
            "hidden": {
                "dynprompt": "DYNPROMPT",
                "unique_id": "UNIQUE_ID",
                "node_def": "NODE_DEFINITION",
            }
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("value0",)
    FUNCTION = "while_loop_close"

    CATEGORY = "InversionDemo Nodes/Flow"

    def explore_dependencies(self, node_id, dynprompt, upstream):
        node_info = dynprompt.get_node(node_id)
        if "inputs" not in node_info:
            return
        for k, v in node_info["inputs"].items():
            if is_link(v):
                parent_id = v[0]
                if parent_id not in upstream:
                    upstream[parent_id] = []
                    self.explore_dependencies(parent_id, dynprompt, upstream)
                upstream[parent_id].append(node_id)

    def collect_contained(self, node_id, upstream, contained):
        if node_id not in upstream:
            return
        for child_id in upstream[node_id]:
            if child_id not in contained:
                contained[child_id] = True
                self.collect_contained(child_id, upstream, contained)


    def while_loop_close(self, flow_control, condition, node_def=None, dynprompt=None, unique_id=None, **kwargs):
        num_inputs = len(node_def['output'])
        if not condition:
            # We're done with the loop
            values = []
            for i in range(num_inputs):
                values.append(kwargs.get("initial_value%d" % i, None))
            return {
                "result": tuple(values),
                # We use 'expansion' just so we can resolve the rawLink inputs
                "expand": GraphBuilder().finalize(),
            }

        assert dynprompt is not None

        # We want to loop
        this_node = dynprompt.get_node(unique_id)
        upstream = {}
        # Get the list of all nodes between the open and close nodes
        self.explore_dependencies(unique_id, dynprompt, upstream)

        contained = {}
        open_node = flow_control[0]
        self.collect_contained(open_node, upstream, contained)
        contained[unique_id] = True
        contained[open_node] = True

        # We'll use the default prefix, but to avoid having node names grow exponentially in size,
        # we'll use "Recurse" for the name of the recursively-generated copy of this node.
        graph = GraphBuilder()
        for node_id in contained:
            original_node = dynprompt.get_node(node_id)
            node = graph.node(original_node["class_type"], "Recurse" if node_id == unique_id else node_id)
            node.set_override_display_id(node_id)
        for node_id in contained:
            original_node = dynprompt.get_node(node_id)
            node = graph.lookup_node("Recurse" if node_id == unique_id else node_id)
            for k, v in original_node["inputs"].items():
                if is_link(v) and v[0] in contained:
                    parent = graph.lookup_node(v[0])
                    node.set_input(k, parent.out(v[1]))
                else:
                    node.set_input(k, v)
        new_open = graph.lookup_node(open_node)
        for i in range(num_inputs):
            key = "initial_value%d" % i
            new_open.set_input(key, kwargs.get(key, None))
        my_clone = graph.lookup_node("Recurse" )
        result = map(lambda x: my_clone.out(x), range(num_inputs))
        return {
            "result": tuple(result),
            "expand": graph.finalize(),
        }

@VariantSupport()
class ExecutionBlockerNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "input": ("*",),
                "block": ("BOOLEAN",),
                "verbose": ("BOOLEAN", {"default": False}),
            },
        }
        return inputs

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "execution_blocker"

    CATEGORY = "InversionDemo Nodes/Flow"

    def execution_blocker(self, input, block, verbose):
        if block:
            return (ExecutionBlocker("Blocked Execution" if verbose else None),)
        return (input,)

FLOW_CONTROL_NODE_CLASS_MAPPINGS = {
    "WhileLoopOpen": WhileLoopOpen,
    "WhileLoopClose": WhileLoopClose,
    "ExecutionBlocker": ExecutionBlockerNode,
}
FLOW_CONTROL_NODE_DISPLAY_NAME_MAPPINGS = {
    "WhileLoopOpen": "While Loop Open",
    "WhileLoopClose": "While Loop Close",
    "ExecutionBlocker": "Execution Blocker",
}
