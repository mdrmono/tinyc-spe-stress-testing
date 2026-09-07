# Skeletal Program Enumeration Term Project
# Authors: Rashed Hadi (rmh7), Kavi Godden (kgodden), Manuel Delfin(mda99)

from .spe_types import Variable, Hole, ParseResult
import tree_sitter_c as tsc
from tree_sitter import Language, Parser


# parser class for parsing c programs
# this parser includes logic that allows us:
# - to find all the holes in the program
# - track the function scopes
# - track the block scopes inside funciton
# - track the variable structure and types
# - create a skeleton structure of the program allowing us to
#   to generate programs with the enumerations after finding the variants

class SPEParser:
    # parser intialization
    def __init__(self):
        C_LANGUAGE = Language(tsc.language())
        self.parser = Parser(C_LANGUAGE)

        self.variables = {}
        self.scope_stack = ["global"]
        self.variable_placeholders = {}
        self.variable_counter = 0


    def parse(self, source_code):
        # intial empty source code check 
        if not source_code.strip():
            return ParseResult(variables=[], holes=[], skeleton_structure={}, scopes=["global"]) 

        tree = self.parser.parse(bytes(source_code, "utf8"))

        # clear all variables and scopes before parsing
        self.variables.clear()
        self.scope_stack = ["global"]
        self.variable_placeholders.clear()
        self.variable_counter = 0

        # traverse the tree and get the structure starting at root node
        structure = self.traverse_node(tree.root_node)

        # the first step is to find all the holes in the program
        raw_holes = self.find_holes(tree)
        holes = []
        # convert the raw holes to holes type
        for h in raw_holes:
            holes.append(
                Hole(
                    start=h["start"],
                    end=h["end"],
                    type_info=h["type"],
                    scope=h["scope"],
                )
            )

        scope_set = {v.scope for v in self.variables.values()}
        scope_set.update(h.scope for h in holes)
        scopes = sorted(scope_set)

        global_hole_indices = [idx for idx, h in enumerate(holes) if h.scope == "global"]

        return ParseResult(
            variables=list(self.variables.values()),
            holes=holes,
            skeleton_structure=structure,
            scopes=scopes,
            global_hole_indices=global_hole_indices,
        )

    def traverse_node(self, node, depth=0):
        if node.type in ["compound_statement", "function_definition"]:
            if node.type == "function_definition":
                func_name = self.get_function_name(node)
                if func_name is not None:
                    self.scope_stack.append(func_name)
                else:
                    self.scope_stack.append(f"function_{depth}")
            else:
                self.scope_stack.append(f"block_{depth}")

        node_info = {
            "type": node.type,
            "children": [],
            "skeleton_placeholder": None,
        }

        # split up node type handling
        if node.type in ["declaration", "parameter_declaration"]:
            self.process_declaration(node)

        if node.type == "identifier" and self.is_variable_identifier(node):
            var_name = node.text.decode("utf8")
            placeholder = self.get_or_create_variable_placeholder(var_name, node)
            node_info["skeleton_placeholder"] = placeholder

        for child in node.children:
            node_info["children"].append(self.traverse_node(child, depth + 1))

        if node.type in ["compound_statement", "function_definition"]:
            if len(self.scope_stack) > 1:
                self.scope_stack.pop()

        return node_info

    # function name from the declaration node
    def get_function_name(self, func_node):
        for child in func_node.children:
            if child.type == "function_declarator":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        return subchild.text.decode("utf8")
        return None

    # function to process the declaration node
    def process_declaration(self, decl_node):
        type_info = "unknown"
        variables_in_decl = []

        for child in decl_node.children:
            if child.type in ["primitive_type", "type_identifier", "struct_specifier", "union_specifier"]:
                type_info = child.text.decode("utf8")
                break

        for child in decl_node.children:
            if child.type == "init_declarator":
                var_info = self.extract_variable_from_declarator(child, type_info)
                if var_info is not None:
                    variables_in_decl.append(var_info)
            elif child.type in ["identifier", "pointer_declarator", "array_declarator"]:
                var_info = self.extract_variable_from_declarator(child, type_info)
                if var_info is not None:
                    variables_in_decl.append(var_info)

        # after extraction the variables, find their scope and store them
        for var_info in variables_in_decl:
            if var_info["name"] not in self.variables:
                declared_scope = self.determine_scope_label(decl_node)
                self.variables[var_info["name"]] = Variable(
                    name=var_info["name"],
                    type_info=var_info["type"],
                    scope=declared_scope,
                    is_pointer=var_info["is_pointer"],
                    is_array=var_info["is_array"],
                )

    # function thta extracts the variabel from the declarator node
    def extract_variable_from_declarator(self, declarator_node, base_type):
        is_pointer = False
        is_array = False
        var_name = None

        # we will work on the node's children as well
        current_node = declarator_node
        if current_node.type == "init_declarator":
            for child in current_node.children:
                if child.type in ["identifier", "pointer_declarator", "array_declarator"]:
                    current_node = child
                    break

        while current_node is not None:
            if current_node.type == "identifier":
                var_name = current_node.text.decode("utf8")
                break
            elif current_node.type == "pointer_declarator":
                is_pointer = True
                advanced = False
                for child in current_node.children:
                    if child.type in ["identifier", "pointer_declarator", "array_declarator"]:
                        current_node = child
                        advanced = True
                        break
                if advanced is False:
                    break
            elif current_node.type == "array_declarator":
                is_array = True
                advanced = False
                for child in current_node.children:
                    if child.type in ["identifier", "pointer_declarator", "array_declarator"]:
                        current_node = child
                        advanced = True
                        break
                if advanced is False:
                    break
            else:
                break

        if var_name is None:
            return None

        return {
            "name": var_name,
            "type": base_type,
            "is_pointer": is_pointer,
            "is_array": is_array,
        }


    def infer_variable_type(self, node):
        parent = node.parent
        var_name = node.text.decode("utf8")

        if var_name in self.variables:
            return self.variables[var_name].type_info

        current = parent
        while current is not None:
            if current.type in ["declaration", "parameter_declaration"]:
                for child in current.children:
                    if child.type in ["primitive_type", "type_identifier", "struct_specifier"]:
                        return child.text.decode("utf8")
            elif current.type == "function_definition":
                for child in current.children:
                    if child.type == "function_declarator":
                        param_list = self.find_parameter_list(child)
                        if param_list is not None:
                            param_type = self.find_parameter_type(param_list, var_name)
                            if param_type is not None:
                                return param_type
            current = current.parent

        return "unknown"

    def find_parameter_list(self, func_declarator):
        for child in func_declarator.children:
            if child.type == "parameter_list":
                return child
        return None

    def find_parameter_type(self, param_list, var_name):
        for child in param_list.children:
            if child.type == "parameter_declaration":
                has_var = False
                param_type = "unknown"
                for subchild in child.children:
                    if subchild.type in ["primitive_type", "type_identifier"]:
                        param_type = subchild.text.decode("utf8")
                    elif subchild.type == "identifier" and subchild.text.decode("utf8") == var_name:
                        has_var = True
                if has_var is True:
                    return param_type
        return None

    # helper function to determine if the node is a variable identifier
    def is_variable_identifier(self, node):
        parent = node.parent
        var_name = node.text.decode("utf8")

        # check different cases where node is not a variable identifier type and return false
        if parent is not None and parent.type == "call_expression":
            if parent.children and parent.children[0] == node:
                return False
        if parent is not None and parent.type == "function_declarator":
            return False
        if parent is not None and parent.type in ["type_identifier", "primitive_type"]:
            return False
        if parent is not None and parent.type in ["struct_specifier", "union_specifier", "enum_specifier"]:
            return False
        if parent is not None and parent.type == "labeled_statement":
            return False
        if parent is not None and parent.type == "goto_statement":
            return False

        # list of c keywords that we dont want to consider as variable identifiers
        c_keywords = {
            "auto", "break", "case", "char", "const", "continue", "default", "do",
            "double", "else", "enum", "extern", "float", "for", "goto", "if",
            "int", "long", "register", "return", "short", "signed", "sizeof",
            "static", "struct", "switch", "typedef", "union", "unsigned", "void",
            "volatile", "while",
        }

        if var_name in c_keywords:
            return False

        return True

    # function to get or create a variable placeholder
    # this is used to record the variable as a variable type so we can 
    # store it in the skeleton structure 
    def get_or_create_variable_placeholder(self, var_name, node):
        if var_name in self.variable_placeholders:
            return self.variable_placeholders[var_name]

        placeholder = f"VAR_{self.variable_counter}"
        self.variable_placeholders[var_name] = placeholder
        self.variable_counter += 1

        if var_name not in self.variables:
            var_type = self.infer_variable_type(node)
            self.variables[var_name] = Variable(
                name=var_name,
                type_info=var_type,
                scope=self.scope_stack[-1],
            )

        return placeholder

    # function that is going to walk the tree structure 
    # and return list of holes
    def find_holes(self, tree):
        holes = []

        def walk(n):
            if n.type == "identifier" and self.is_variable_identifier(n):
                var_type = self.infer_variable_type(n)
                scope = self.determine_scope_label(n)
                holes.append(
                    {
                        "start": n.start_byte,
                        "end": n.end_byte,
                        "type": var_type,
                        "scope": scope,
                    }
                )
            for ch in n.children:
                walk(ch)

        walk(tree.root_node)
        holes.sort(key=lambda h: h["start"])
        return holes

    # this function is used to get the scope of each node ni the tree
    # which is essencial to add scoping to the enumeration so that variables
    # in inner scope are not used in outer scopes
    def determine_scope_label(self, node):
        current = node
        block_depth = 0
        func_name = None
        while current is not None:
            if current.type == "compound_statement":
                block_depth += 1
            elif current.type == "function_definition" and func_name is None:
                func_name = self.get_function_name(current) or "function"
            current = current.parent

        if func_name is None:
            func_name = "global"

        if block_depth <= 1:
            return func_name

        return f"{func_name}:block_{block_depth - 1}"

# function called by runners to start parsing source code
def parse_c_program(source_code):
    parser = SPEParser()
    return parser.parse(source_code)