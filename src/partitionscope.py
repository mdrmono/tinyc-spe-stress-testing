# Skeletal Program Enumeration Term Project
# Authors: Rashed Hadi (rmh7), Kavi Godden (kgodden), Manuel Delfin(mda99)

from itertools import combinations, permutations, product

def partition_scope(S_L, G, l_i, variable_pool, i, total_scopes, global_vars): 
    u = len(l_i)
    v = len(variable_pool)
   
    for k in range(1, u):
        l = combinations(l_i, k)
        G = G.union(l)
        l_prime = l_i.difference(l)
        for j in range(1, v):
            S_li = partition(l_prime, j)
            S_pl = S_L
            S_L = product(S_L, S_li)

            if i != total_scopes - 1:
                partition_scope(S_L, G, l_i, variable_pool, i + 1, total_scopes)
            else:
                S_G = partition_prime(G, global_vars)
                return product(S_G, S_L)
            S_L = S_pl
        G = G.difference(l)

def partition(Q, k):
    Q = list(Q)
    res = set()
    for assignment in product(range(k), repeat=len(Q)):
        subsets = [set() for _ in range(k)]
        for elem, bin_index in zip(Q, assignment):
            subsets[bin_index].add(elem)
        # Make each subset hashable and the whole partition hashable
        res.add(tuple(frozenset(s) for s in subsets))
    return res 

def partition_prime(s, k):
    s = list(s)
    if k == 1:
        return [[set(s)]]
    elif len(s) == k:
        return [[{x} for x in s]]
    else:
        result = []
        first = s[0]
        
        for smaller in partition_prime(s[1:], k - 1):
            result.append([set([first])] + smaller)
        
        for smaller in partition_prime(s[1:], k):
            for i in range(len(smaller)):
                new_part = smaller[i] | {first}
                result.append(smaller[:i] + [new_part] + smaller[i+1:])
        
        return result
