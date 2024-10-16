from comfy_execution.graph_utils import GraphBuilder
import torch
from .tools import VariantSupport
from comfy_execution.node_utils import TemplateTypeSupport

@TemplateTypeSupport()
class AccumulateNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "to_add": ("<T>", {"forceInput": True}),
            },
            "optional": {
                "accumulation": ("ACCUMULATION<T>", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("ACCUMULATION<T>",)
    RETURN_NAMES = ("accumulation",)
    FUNCTION = "accumulate"

    CATEGORY = "InversionDemo Nodes/Lists"

    def accumulate(self, to_add, accumulation = None):
        if accumulation is None:
            value = [to_add]
        else:
            value = accumulation["accum"] + [to_add]
        return ({"accum": value},)

@TemplateTypeSupport()
class AccumulationHeadNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "accumulation": ("ACCUMULATION<T>", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("ACCUMULATION<T>", "<T>",)
    RETURN_NAMES = ("accumulation", "head")
    FUNCTION = "accumulation_head"

    CATEGORY = "InversionDemo Nodes/Lists"

    def accumulation_head(self, accumulation):
        accum = accumulation["accum"]
        if len(accum) == 0:
            return (accumulation, None)
        else:
            return ({"accum": accum[1:]}, accum[0])

@TemplateTypeSupport()
class AccumulationTailNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "accumulation": ("ACCUMULATION<T>", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("ACCUMULATION<T>", "<T>",)
    RETURN_NAMES = ("accumulation", "tail")
    FUNCTION = "accumulation_tail"

    CATEGORY = "InversionDemo Nodes/Lists"

    def accumulation_tail(self, accumulation):
        accum = accumulation["accum"]
        if len(accum) == 0:
            return (None, accumulation)
        else:
            return ({"accum": accum[:-1]}, accum[-1])

@TemplateTypeSupport()
class AccumulationToListNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "accumulation": ("ACCUMULATION<T>", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("<T>",)
    RETURN_NAMES = ("list",)
    OUTPUT_IS_LIST = (True,)

    FUNCTION = "accumulation_to_list"

    CATEGORY = "InversionDemo Nodes/Lists"

    def accumulation_to_list(self, accumulation):
        return (accumulation["accum"],)

@TemplateTypeSupport()
class ListToAccumulationNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list": ("<T>", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("ACCUMULATION<T>",)
    RETURN_NAMES = ("accumulation",)
    INPUT_IS_LIST = (True,)

    FUNCTION = "list_to_accumulation"

    CATEGORY = "InversionDemo Nodes/Lists"

    def list_to_accumulation(self, list):
        return ({"accum": list},)

@TemplateTypeSupport()
class AccumulationGetLengthNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "accumulation": ("ACCUMULATION<T>", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("length",)

    FUNCTION = "accumlength"

    CATEGORY = "InversionDemo Nodes/Lists"

    def accumlength(self, accumulation):
        return (len(accumulation['accum']),)
        
@TemplateTypeSupport()
class AccumulationGetItemNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "accumulation": ("ACCUMULATION<T>", {"forceInput": True}),
                "index": ("INT", {"default":0, "step":1})
            },
        }

    RETURN_TYPES = ("<T>",)
    RETURN_NAMES = ("item",)

    FUNCTION = "get_item"

    CATEGORY = "InversionDemo Nodes/Lists"

    def get_item(self, accumulation, index):
        return (accumulation['accum'][index],)
        
@TemplateTypeSupport()
class AccumulationSetItemNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "accumulation": ("ACCUMULATION<T>", {"forceInput": True}),
                "index": ("INT", {"default":0, "step":1}),
                "value": ("<T>", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("ACCUMULATION<T>",)
    RETURN_NAMES = ("accumulation",)

    FUNCTION = "set_item"

    CATEGORY = "InversionDemo Nodes/Lists"

    def set_item(self, accumulation, index, value):
        new_accum = accumulation['accum'][:]
        new_accum[index] = value
        return ({"accum": new_accum},)

@VariantSupport()
class IntMathOperation:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "a": ("INT", {"default": 0, "min": -0xffffffffffffffff, "max": 0xffffffffffffffff, "step": 1}),
                "b": ("INT", {"default": 0, "min": -0xffffffffffffffff, "max": 0xffffffffffffffff, "step": 1}),
                "operation": (["add", "subtract", "multiply", "divide", "modulo", "power"],),
            },
        }

    RETURN_TYPES = ("INT",)
    FUNCTION = "int_math_operation"

    CATEGORY = "InversionDemo Nodes/Logic"

    def int_math_operation(self, a, b, operation):
        if operation == "add":
            return (a + b,)
        elif operation == "subtract":
            return (a - b,)
        elif operation == "multiply":
            return (a * b,)
        elif operation == "divide":
            return (a // b,)
        elif operation == "modulo":
            return (a % b,)
        elif operation == "power":
            return (a ** b,)


from .flow_control import NUM_FLOW_SOCKETS, VariadicFlowNode
@VariantSupport()
class ForLoopOpen(VariadicFlowNode):
    def __init__(self):
        pass

    @classmethod
    def resolve_dynamic_types(cls, input_types, output_types, entangled_types):
        return cls.resolve_dynamic_flow_types(
            ['FLOW_CONTROL', 'INT'],
            ['flow_control', 'remaining'],
            1,
            input_types,
            output_types,
            entangled_types,
        )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "remaining": ("INT", {"default": 1, "min": 0, "max": 100000, "step": 1}),
            },
            "optional": {
                "initial_value1": ("*",{
                    "forceInput": True,
                    "rawLink": True,
                })
            },
            "hidden": {
                "initial_value0": ("*",),
                "node_def": "NODE_DEFINITION",
            }
        }

    RETURN_TYPES = tuple(["FLOW_CONTROL", "INT", "*"])
    RETURN_NAMES = tuple(["flow_control", "remaining", "value1"])
    FUNCTION = "for_loop_open"

    CATEGORY = "InversionDemo Nodes/Flow"

    def for_loop_open(self, remaining, node_def, **kwargs):
        num_inputs = len(node_def['output'])
        graph = GraphBuilder()
        if "initial_value0" in kwargs:
            remaining = kwargs["initial_value0"]
        while_open = graph.node("WhileLoopOpen", condition=remaining, initial_value0=remaining, **{("initial_value%d" % i): kwargs.get("initial_value%d" % i, None) for i in range(1, num_inputs)})
        outputs = [kwargs.get("initial_value%d" % i, None) for i in range(1, num_inputs)]
        return {
            "result": tuple(["stub", remaining] + outputs),
            "expand": graph.finalize(),
        }

@VariantSupport()
class ForLoopClose(VariadicFlowNode):
    def __init__(self):
        pass

    @classmethod
    def resolve_dynamic_types(cls, input_types, output_types, entangled_types):
        return cls.resolve_dynamic_flow_types(
            [],
            [],
            1,
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
                }),
            },
            "optional": {
                "initial_value%d" % i: ("*",{"rawLink": True}) for i in range(1, NUM_FLOW_SOCKETS)
            },
            "hidden": {
                "node_def": "NODE_DEFINITION",
            }
        }

    RETURN_TYPES = tuple(["*"] * (NUM_FLOW_SOCKETS-1))
    RETURN_NAMES = tuple(["value%d" % i for i in range(1, NUM_FLOW_SOCKETS)])
    FUNCTION = "for_loop_close"

    CATEGORY = "InversionDemo Nodes/Flow"

    def for_loop_close(self, flow_control, node_def, **kwargs):
        num_inputs = len(node_def['output'])
        graph = GraphBuilder()
        while_open = flow_control[0]
        # TODO - Requires WAS-ns. Will definitely want to solve before merging
        sub = graph.node("IntMathOperation", operation="subtract", a=[while_open,1], b=1)
        cond = graph.node("ToBoolNode", value=sub.out(0))
        input_values = {("initial_value%d" % i): kwargs.get("initial_value%d" % i, None) for i in range(1, num_inputs)}
        while_close = graph.node("WhileLoopClose",
                flow_control=flow_control,
                condition=cond.out(0),
                initial_value0=sub.out(0),
                **input_values)
        return {
            "result": tuple([while_close.out(i) for i in range(1, num_inputs)]),
            "expand": graph.finalize(),
        }

@VariantSupport()
class DebugPrint:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": ("*",),
                "label": ("STRING", {"multiline": False}),
            },
        }

    RETURN_TYPES = ("*",)
    FUNCTION = "debug_print"

    CATEGORY = "InversionDemo Nodes/Debug"

    def debugtype(self, value):
        if isinstance(value, list):
            result = "["
            for i, v in enumerate(value):
                result += (self.debugtype(v) + ",")
            result += "]"
        elif isinstance(value, tuple):
            result = "("
            for i, v in enumerate(value):
                result += (self.debugtype(v) + ",")
            result += ")"
        elif isinstance(value, dict):
            result = "{"
            for k, v in value.items():
                result += ("%s: %s," % (self.debugtype(k), self.debugtype(v)))
            result += "}"
        elif isinstance(value, str):
            result = "'%s'" % value
        elif isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
            result = str(value)
        elif isinstance(value, torch.Tensor):
            result = "Tensor[%s]" % str(value.shape)
        else:
            result = type(value).__name__
        return result

    def debug_print(self, value, label):
        print("[%s]: %s" % (label, self.debugtype(value)))
        return (value,)

@TemplateTypeSupport()
class MakeListNode:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "value#COUNT": ("<T>", {"forceInput": True}),
            },
            "hidden": {
                "node_def": "NODE_DEFINITION",
            },
        }

    RETURN_TYPES = ("<T>",)
    RETURN_NAMES = ("list",)
    FUNCTION = "make_list"
    OUTPUT_IS_LIST = (True,)

    CATEGORY = "InversionDemo Nodes/Lists"

    def make_list(self, node_def, **kwargs):
        result = []
        for i in range(node_def.get("dynamic_counts", {}).get("COUNT", 0)):
            if "value%d" % i in kwargs:
                result.append(kwargs["value%d" % i])
        return (result,)

UTILITY_NODE_CLASS_MAPPINGS = {
    "AccumulateNode": AccumulateNode,
    "AccumulationHeadNode": AccumulationHeadNode,
    "AccumulationTailNode": AccumulationTailNode,
    "AccumulationToListNode": AccumulationToListNode,
    "ListToAccumulationNode": ListToAccumulationNode,
    "AccumulationGetLengthNode": AccumulationGetLengthNode,
    "AccumulationGetItemNode": AccumulationGetItemNode,
    "AccumulationSetItemNode": AccumulationSetItemNode,
    "ForLoopOpen": ForLoopOpen,
    "ForLoopClose": ForLoopClose,
    "IntMathOperation": IntMathOperation,
    "DebugPrint": DebugPrint,
    "MakeListNode": MakeListNode,
}
UTILITY_NODE_DISPLAY_NAME_MAPPINGS = {
    "AccumulateNode": "Accumulate",
    "AccumulationHeadNode": "Accumulation Head",
    "AccumulationTailNode": "Accumulation Tail",
    "AccumulationToListNode": "Accumulation to List",
    "ListToAccumulationNode": "List to Accumulation",
    "AccumulationGetLengthNode": "Accumulation Get Length",
    "AccumulationGetItemNode": "Accumulation Get Item",
    "AccumulationSetItemNode": "Accumulation Set Item",
    "ForLoopOpen": "For Loop Open",
    "ForLoopClose": "For Loop Close",
    "IntMathOperation": "Int Math Operation",
    "DebugPrint": "Debug Print",
    "MakeListNode": "Make List",
}
