import re
from typing import Optional, Tuple
def MakeSmartType(t):
    if isinstance(t, str):
        return SmartType(t)
    return t

class SmartType(str):
    def __ne__(self, other):
        if self == "*" or other == "*":
            return False
        selfset = set(self.split(','))
        otherset = set(other.split(','))
        return not selfset.issubset(otherset)

def VariantSupport():
    def decorator(cls):
        if hasattr(cls, "INPUT_TYPES"):
            old_input_types = getattr(cls, "INPUT_TYPES")
            def new_input_types(*args, **kwargs):
                types = old_input_types(*args, **kwargs)
                for category in ["required", "optional"]:
                    if category not in types:
                        continue
                    for key, value in types[category].items():
                        if isinstance(value, tuple):
                            types[category][key] = (MakeSmartType(value[0]),) + value[1:]
                return types
            setattr(cls, "INPUT_TYPES", new_input_types)
        if hasattr(cls, "RETURN_TYPES"):
            old_return_types = cls.RETURN_TYPES
            setattr(cls, "RETURN_TYPES", tuple(MakeSmartType(x) for x in old_return_types))
        if hasattr(cls, "VALIDATE_INPUTS"):
            # Reflection is used to determine what the function signature is, so we can't just change the function signature
            raise NotImplementedError("VariantSupport does not support VALIDATE_INPUTS yet")
        else:
            def validate_inputs(input_types):
                inputs = cls.INPUT_TYPES()
                for key, value in input_types.items():
                    if isinstance(value, SmartType):
                        continue
                    if "required" in inputs and key in inputs["required"]:
                        expected_type = inputs["required"][key][0]
                    elif "optional" in inputs and key in inputs["optional"]:
                        expected_type = inputs["optional"][key][0]
                    else:
                        expected_type = None
                    if expected_type is not None and MakeSmartType(value) != expected_type:
                        return f"Invalid type of {key}: {value} (expected {expected_type})"
                return True
            setattr(cls, "VALIDATE_INPUTS", validate_inputs)
        return cls
    return decorator

def type_intersection(a: str, b: str) -> str:
    if a == "*":
        return b
    if b == "*":
        return a
    if a == b:
        return a
    aset = set(a.split(','))
    bset = set(b.split(','))
    intersection = aset.intersection(bset)
    if len(intersection) == 0:
        return "*"
    return ",".join(intersection)

naked_template_regex = re.compile(r"^<(.+)>$")
qualified_template_regex = re.compile(r"^(.+)<(.+)>$")
accum_regex = re.compile(r"ACCUMULATION<(.+)>")

empty_lookup = {}
def template_to_type(template, key_lookup=empty_lookup):
    templ_match = naked_template_regex.match(template)
    if templ_match:
        return key_lookup.get(templ_match.group(1), "*")
    templ_match = qualified_template_regex.match(template)
    if templ_match:
        resolved = key_lookup.get(templ_match.group(2), "*")
        return qualified_template_regex.sub(r"\1<%s>" % resolved, template)
    return template

def determine_template_value(template: str, actual_type: str) -> Tuple[Optional[str], Optional[str]]:
    templ_match = naked_template_regex.match(template)
    if templ_match:
        return templ_match.group(1), actual_type
    templ_match = qualified_template_regex.match(template)
    actual_match = qualified_template_regex.match(actual_type)
    if templ_match and actual_match and templ_match.group(1) == actual_match.group(1):
        return templ_match.group(2), actual_match.group(2)

    return None, None

def TemplateTypeSupport():
    def decorator(cls):
        old_input_types = getattr(cls, "INPUT_TYPES")
        def new_input_types(cls):
            types = old_input_types()
            for category in ["required", "optional"]:
                if category not in types:
                    continue
                for key, value in types[category].items():
                    types[category][key] = (template_to_type(value[0]),) + value[1:]
            return types
        setattr(cls, "INPUT_TYPES", classmethod(new_input_types))
        old_outputs = getattr(cls, "RETURN_TYPES")
        setattr(cls, "RETURN_TYPES", tuple(template_to_type(x) for x in old_outputs))

        def resolve_dynamic_types(cls, input_types, output_types, entangled_types):
            resolved = {}
            inputs = old_input_types()
            for category in ["required", "optional"]:
                if category not in inputs:
                    continue
                for key, value in inputs[category].items():
                    if key in input_types:
                        tkey, tvalue = determine_template_value(value[0], input_types[key])
                        if tkey is not None and tvalue is not None:
                            resolved[tkey] = type_intersection(resolved.get(tkey, "*"), tvalue)
            for i in range(len(old_outputs)):
                output_name = cls.RETURN_NAMES[i]
                if output_name in output_types:
                    for output_type in output_types[output_name]:
                        tkey, tvalue = determine_template_value(old_outputs[i], output_type)
                        if tkey is not None and tvalue is not None:
                            resolved[tkey] = type_intersection(resolved.get(tkey, "*"), tvalue)

            for category in ["required", "optional"]:
                if category not in inputs:
                    continue
                for key, value in inputs[category].items():
                    inputs[category][key] = (template_to_type(value[0], resolved),) + value[1:]
            outputs = (template_to_type(x, resolved) for x in old_outputs)
            return {
                "input": inputs,
                "output": tuple(outputs),
                "output_name": cls.RETURN_NAMES,
            }
        setattr(cls, "resolve_dynamic_types", classmethod(resolve_dynamic_types))
        return cls
    return decorator
