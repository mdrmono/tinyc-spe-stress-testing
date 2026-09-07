# Skeletal Program Enumeration Term Project
# Authors: Rashed Hadi (rmh7), Kavi Godden (kgodden), Manuel Delfin(mda99)

from __future__ import annotations
from .spe_types import ParseResult, Variable, Hole
from .partitionscope import partition, partition_scope as p_scope

# this file attempts to implement the algorithm 1 from the paper
# this function copies the same layout as the pseudocode in Algorithm 1
def enumerate_programs_algo1(parse):

    # Check total number of holes to prevent stack explosion
    # before adding this we would enumerate huge programs and os would kill
    # the process due to high memory usage
    total_holes = len(parse.holes)
    if total_holes > 10:
        print(f"     ERROR: Program has {total_holes} holes, Aborting!")
        return []
    
    skeleton = parse.skeleton_structure
    S = [tuple()]
    G_global_indices = set(parse.global_hole_indices)
    scope_order = get_function_order(skeleton, parse)

    for scope in scope_order:
        # functions are already normalized, this method does nothing
        normalize_function(scope, skeleton, parse)

        # H_f and v_f are the holes and visible variables in this function scope
        H_f = get_H_f(parse, scope)
        v_f, G_f = get_vars(parse, scope)

        S_f_prime = compute_partitions(H_f, len(v_f))

        S_f = []
        S_L = []

        # PartitionScope
        S_f = partition_scope(S_L, v_f, G_f, H_f, G_global_indices)

        S_f = union_S_f(S_f, list(S_f_prime))

        S = combine_across_functions(S, S_f)
    
    outputs = generate_programs(parse, S)
    return outputs


# this function is used to get the order (hierarchy) of the functions/blocks
def get_function_order(P, parse):
    scope_names = set()

    # first add all the scopes
    if parse.global_hole_indices or any(v.scope == "global" for v in parse.variables):
        scope_names.add("global")
    
    for scope_label in parse.scopes:
        if scope_label:
            scope_names.add(scope_label)

    # sort them according to the scope naming from parser
    def scope_sort_key(scope):
        if scope == "global":
            return (0, "", 0)
        # in parser, scops are names like function_name:block_number
        # so we need to split them and get the function and block scope
        if ":" in scope:
            func, block = scope.split(":", 1)
            block_num = 0
            if block.startswith("block_"):
                try:
                    block_num = int(block.split("_")[1])
                except (IndexError, ValueError):
                    block_num = 0
            return (1, func, block_num)
        else:
            return (1, scope, -1)

    ordered_scopes = sorted(scope_names, key=scope_sort_key)
    return ordered_scopes


# unimplemented, not sure what this does, left empty for further extention
def normalize_function(f, P, parse):
    return None

# collect holes in function's scope
def get_H_f(parse, scope):
    H_f = []

    for h in parse.holes:
        if h.scope == scope:
            H_f.append(h)

    return H_f

# get variables in the function's scope
def get_vars(parse, scope):
    # collecting both local and global
    locals_in_scope = []
    globals_all = []

    def is_variable_visible_in_scope(var_scope, target_scope):
        if var_scope == "global":
            return False
        if var_scope == target_scope:
            return True
        
        if target_scope.startswith(var_scope + ":"):
            return True
        
        if ":" in target_scope and ":" not in var_scope:
            func_name = target_scope.split(":")[0]
            return var_scope == func_name
            
        return False

    for v in parse.variables:
        if v.scope == "global":
            globals_all.append(v)
        else:
            if scope == "global":
                pass
            else:
                if is_variable_visible_in_scope(v.scope, scope):
                    locals_in_scope.append(v)

    # sort before returning
    v_f_sorted = sorted(locals_in_scope, key=lambda x: (x.name, x.scope))
    G_f_sorted = sorted(globals_all, key=lambda x: (x.name, x.scope))

    return v_f_sorted, G_f_sorted


# we are computing the partitions using restricted growth strings expalined in 
# chapter 4 of the paper, especially 4.1.2
def compute_partitions(H_f, k):
    n = len(H_f)
    if n == 0:
        return [tuple()]
    if k <= 0 or k > n:
        return []
    if k == 1:
        return [tuple([frozenset(range(n))])]
    
    result = compute_rgs(n, k)
    return result


def compute_rgs(n, k):
    all_partitions = []
    
    for num_vars in range(1, k + 1):
        partitions = rgs_for_vars(n, num_vars, k)
        all_partitions.extend(partitions)
    
    return all_partitions


def rgs_for_vars(n, exact_vars, total_vars):
    if exact_vars == 1:
        result = [frozenset(range(n))]
        while len(result) < total_vars:
            result.append(frozenset())
        return [tuple(result)]
    
    def is_valid_rgs(rgs):
        if not rgs:
            return False
        if rgs[0] != 0:
            return False
        
        max_seen = 0
        for i in range(1, len(rgs)):
            if rgs[i] > max_seen + 1:
                return False
            max_seen = max(max_seen, rgs[i])
        
        return len(set(rgs)) == exact_vars
    
    def rgs_to_partition(rgs):
        partition_sets = [set() for _ in range(total_vars)]
        for hole_idx, var_idx in enumerate(rgs):
            partition_sets[var_idx].add(hole_idx)
        return tuple(frozenset(s) for s in partition_sets)
    
    valid_partitions = []
    call_count = 0
    
    # using: a1 = 0 and ai+1 <= 1 + max(a1,...,ai) if i E [1,n)
    def generate_rgs(current_rgs, position):
        nonlocal call_count
        call_count += 1
        
        if position == n:
            if is_valid_rgs(current_rgs):
                partition = rgs_to_partition(current_rgs)
                valid_partitions.append(partition)
            return
        
        if position == 0:
            generate_rgs([0], 1)
        else:
            max_seen = max(current_rgs)
            for var_idx in range(max_seen + 2):
                if var_idx < exact_vars:
                    generate_rgs(current_rgs + [var_idx], position + 1)
    
    generate_rgs([], 0)
    return valid_partitions
    
    
def partition_scope(S_f_prime, v_f, G_f, H_f, G_global_indices):
    #setup input so partition scope alg in partitionscope.py can be used
    S_L_input = list(S_f_prime)
    G_accumulator = set(G_global_indices)
    l_i = set(range(len(H_f)))
    variable_pool = list(v_f) + list(G_f)
    i = 0
    total_scopes = 1
    global_vars_count = len(G_f)

    try:
        legacy_out = p_scope(S_L_input, G_accumulator, l_i, variable_pool, i, total_scopes, global_vars_count)
    except Exception:
        return S_L_input

    if legacy_out is None:
        return S_L_input

    normalized = []
    for item in legacy_out:
        if isinstance(item, tuple) and all(hasattr(x, "__iter__") for x in item):
            if all(isinstance(x, frozenset) for x in item):
                normalized.append(item)
                continue
            if len(item) == 2:
                maybe_part = item[1]
                if isinstance(maybe_part, tuple) and all(isinstance(x, frozenset) for x in maybe_part):
                    normalized.append(maybe_part)
                    continue

    if len(normalized) == 0:
        return S_L_input

    return normalized

# union of sets S_f and S_L
def union_S_f(S_f, S_L):
    if len(S_f) == 0:
        return list(S_L)

    seen = set()
    out = []

    for p in S_f:
        if p in seen:
            continue
        out.append(p)
        seen.add(p)

    for p in S_L:
        if p in seen:
            continue
        out.append(p)
        seen.add(p)

    return out

# take the cross product of S and S_f
def combine_across_functions(S, S_f):
    if len(S) == 0:
        return [(x,) for x in S_f]

    if len(S_f) == 0:
        return []

    if not isinstance(S[0], tuple):
        S = [(x,) for x in S]

    combined = []
    for prefix in S:
        for choice in S_f:
            combined.append(prefix + (choice,))
    return combined


# wrapping each partiton with a payload allow us to rebuild the program for generation
def wrap_partition_to_payload(func_name, part, H_f, variable_pool):
    assignment = [-1] * len(H_f)
    for var_idx, hole_set in enumerate(part):
        for h_idx in hole_set:
            assignment[h_idx] = var_idx

    payload = {
        "function": func_name,
        "holes": [
            {
                "index": i,
                "start": h.start,
                "end": h.end,
                "scope": h.scope,
                "type": h.type_info,
            }
            for i, h in enumerate(H_f)
        ],
        "assignments": [
            {
                "hole_index": i,
                "var_index": var_idx,
                "var_name": variable_pool[var_idx].name,
                "var_scope": variable_pool[var_idx].scope,
                "var_type": variable_pool[var_idx].type_info,
            }
            for i, var_idx in enumerate(assignment)
        ],
        "variable_pool": [
            {"name": v.name, "scope": v.scope, "type": v.type_info}
            for v in variable_pool
        ],
    }
    return payload

# final function to generate the variants as c program
# connects the partitions with the wrappers to to provide to the generator
def generate_programs(parse, S):
    function_order = get_function_order(parse.skeleton_structure, parse)

    globals_list = [v for v in parse.variables if v.scope == "global"]
    holes_by_func = {f: get_H_f(parse, f) for f in function_order}
    vars_by_func = {f: get_vars(parse, f)[0] for f in function_order}

    program_vectors = []
    for combo in S:
        if not isinstance(combo, tuple):
            combo = (combo,)

        by_func = {}
        for idx, f in enumerate(function_order):
            part = combo[idx] if idx < len(combo) else tuple()
            H_f = holes_by_func.get(f, [])
            variable_pool = list(vars_by_func.get(f, [])) + list(globals_list)
            payload = wrap_partition_to_payload(f, part, H_f, variable_pool)
            by_func[f] = payload

        program_vectors.append({"by_function": by_func})

    return program_vectors
