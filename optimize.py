import syntax 
import function_registry

import transform
from simplify import Simplify
from inline import Inliner

pipeline = [Simplify, Inliner, Simplify] 

# map names of unoptimized typed functions to 
# names of optimized 
_optimized_cache = {}
def optimize(fn, copy = False):
  if isinstance(fn, syntax.Fn):
    raise RuntimeError("Can't optimize untyped functions")
  elif isinstance(fn, str):
    assert fn in function_registry.typed_functions, \
      "Unknown typed function: " + str(fn)
      
    fn = function_registry.typed_functions[fn]
  else:
    assert isinstance(fn, syntax.TypedFn)
      
  if fn.name in _optimized_cache:
    return _optimized_cache[fn.name]
  else:  
    opt = transform.apply_pipeline(fn, pipeline, copy = copy)
    _optimized_cache[fn.name] = opt
    return opt 