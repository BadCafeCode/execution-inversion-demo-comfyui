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
variadic_template_regex = re.compile(r"([^<]+)#([^>]+)")
variadic_suffix_regex =   re.compile(r"([^<]+)(\d+)")

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

# Returns the 'key' and 'value' of the template (if any)
def determine_template_value(template: str, actual_type: str) -> Tuple[Optional[str], Optional[str]]:
    templ_match = naked_template_regex.match(template)
    if templ_match:
        return templ_match.group(1), actual_type
    templ_match = qualified_template_regex.match(template)
    actual_match = qualified_template_regex.match(actual_type)
    if templ_match and actual_match and templ_match.group(1) == actual_match.group(1):
        return templ_match.group(2), actual_match.group(2)
    return None, None

def determine_variadic_group(template: str) -> Tuple[Optional[str], Optional[str]]:
    variadic_match = variadic_template_regex.match(template)
    if variadic_match:
        return variadic_match.group(1), variadic_match.group(2)
    return None, None

def replace_variadic_suffix(template: str, index: int) -> str:
    return variadic_template_regex.sub(lambda match: match.group(1) + str(index), template)

def determine_variadic_suffix(template: str) -> Tuple[Optional[str], Optional[int]]:
    variadic_match = variadic_suffix_regex.match(template)
    if variadic_match:
        return variadic_match.group(1), int(variadic_match.group(2))
    return None, None

def TemplateTypeSupport():
    def decorator(cls):
        old_input_types = getattr(cls, "INPUT_TYPES")
        def new_input_types(cls):
            old_types = old_input_types()
            new_types = {
                "required": {},
                "optional": {},
                "hidden": old_types.get("hidden", {}),
            }
            for category in ["required", "optional"]:
                if category not in old_types:
                    continue
                for key, value in old_types[category].items():
                    new_types[category][replace_variadic_suffix(key, 1)] = (template_to_type(value[0]),) + value[1:]
            return new_types
        setattr(cls, "INPUT_TYPES", classmethod(new_input_types))
        old_outputs = getattr(cls, "RETURN_TYPES")
        setattr(cls, "RETURN_TYPES", tuple(template_to_type(x) for x in old_outputs))

        def resolve_dynamic_types(cls, input_types, output_types, entangled_types):
            original_inputs = old_input_types()

            # Step 1 - Find all variadic groups and determine their maximum used index
            variadic_group_map = {}
            max_group_index = {}
            for category in ["required", "optional"]:
                for key, value in original_inputs.get(category, {}).items():
                    root, group = determine_variadic_group(key)
                    if root is not None and group is not None:
                        variadic_group_map[root] = group
            for type_map in [input_types, output_types]:
                for key in type_map.keys():
                    root, index = determine_variadic_suffix(key)
                    if root is not None and index is not None:
                        if root in variadic_group_map:
                            group = variadic_group_map[root]
                            max_group_index[group] = max(max_group_index.get(group, 0), index)

            # Step 2 - Create variadic arguments
            variadic_inputs = {
                "required": {},
                "optional": {},
            }
            for category in ["required", "optional"]:
                for key, value in original_inputs.get(category, {}).items():
                    root, group = determine_variadic_group(key)
                    if root is None or group is None:
                        # Copy it over as-is
                        variadic_inputs[category][key] = value
                    else:
                        for i in range(1, max_group_index.get(group, 0) + 2):
                            # Also replace any variadic suffixes in the type (for use with templates)
                            input_type = value[0]
                            if isinstance(input_type, str):
                                input_type = replace_variadic_suffix(input_type, i)
                            variadic_inputs[category][replace_variadic_suffix(key, i)] = (input_type,value[1])

            # Step 3 - Resolve template arguments
            resolved = {}
            for category in ["required", "optional"]:
                for key, value in variadic_inputs[category].items():
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

            # Step 4 - Replace templates with resolved types
            final_inputs = {
                "required": {},
                "optional": {},
                "hidden": original_inputs.get("hidden", {}),
            }
            for category in ["required", "optional"]:
                for key, value in variadic_inputs[category].items():
                    final_inputs[category][key] = (template_to_type(value[0], resolved),) + value[1:]
            outputs = (template_to_type(x, resolved) for x in old_outputs)
            return {
                "input": final_inputs,
                "output": tuple(outputs),
                "output_name": cls.RETURN_NAMES,
                "dynamic_counts": max_group_index,
            }
        setattr(cls, "resolve_dynamic_types", classmethod(resolve_dynamic_types))
        return cls
    return decorator
