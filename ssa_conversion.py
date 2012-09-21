import ast 
import ssa 

class NameNotFound(Exception):
  def __init__(self, name):
    self.name = name 
    
class NameSupply:
  versions = {}
  original_names = {}
  
  @staticmethod
  def get(self, name):
    version = self.versions.get(name)
    if version is None:
      raise NameNotFound(name)
    else:
      return "%s.%d" % (name, version)
    
  @staticmethod  
  def fresh(self, name):
    version = self.versions.get(name, 0) + 1 
    self.versions[name] = version
    ssa_name = "%s.%d" % (name, version)
    self.original_names[ssa_name] = name
    return ssa_name 
  


class ScopedEnv:  
  def __init__(self, current_scope = None,  outer_env = None):
    if current_scope is None:
      current_scope = {}
    
    if outer_env is None:
      outer_env = {}
      
    self.scopes = [current_scope]
    
    # a top-level function will point to an environment for globals
    # and a nested function points to the environment of its enclosing fn
    self.outer_env = outer_env
     

    
  def fresh(self, name):
    fresh_name = NameSupply.fresh(name)
    self.scopes[-1][name] = fresh_name 
    return fresh_name
  
  def push_scope(self, scope = None):
    if scope is None:
      scope = {}
    self.scopes.append(scope)
  
  def pop_scope(self):
    return self.scopes.pop()
  
  def __getitem__(self, key):
    for scope in reversed(self.scopes):
      if key in scope:
        return scope[key]
    raise NameNotFound(key)

  def __contains__(self, key):
    for scope in reversed(self.scopes):
      if key in scope: 
        return True
    return False 

  def is_nonlocal(self, key):
    """Recursively move up the chain of 'outer_env' links to find if
    a variable has been bound outside the current function
    """
    if self.outer_env is None:
      return False
    elif key in self.outer_env:
      return True
    elif isinstance(self.outer_env, ScopedEnv):
      return self.outer_env.is_nonlocal(key)
    else:
      return False 


def translate_FunctionDef(node, outer_env = None):
  name, body, args = node.name, node.body, node.args 
  nonlocals =  set([])
  ssa_args = dict(zip(args, map(NameSupply.fresh, args)))
  env = ScopedEnv(current_scope = ssa_args, outer_env = outer_env)
         
  def translate_Name(name):
    """
    Convert a variable name to its versioned SSA identifier and 
    if the name isn't local return it in a one-element set denoting
    which nonlocals get accessed
    """
    if name in env:
      return ssa.Var(env[name])
    # is it at least somewhere in the chain of outer scopes?  
    elif env.is_nonlocal(name):
      nonlocals.add(name)
      ssa_name = env.fresh(name) 
      return ssa.Var(ssa_name)
    else:
      raise NameNotFound(name)
      
  def translate_BinOp(name, op, left, right, env):
    ssa_left = translate_expr(left)
    ssa_right = translate_expr(right)
    ssa.Binop(op, ssa_left, ssa_right)
    
  
  def translate_expr(expr, env):
    if isinstance(expr, ast.BinOp):
      return translate_BinOp(expr.op, expr.left, expr.right)
    elif isinstance(expr, ast.Name):
      return translate_Name(expr.id)
      
    elif isinstance(expr, ast.Num):
      ssa.Const(expr.n) 
      
  def translate_Assign(lhs, rhs, env):
    assert isinstance(lhs, ast.Name)
    ssa_lhs_id = env.fresh(lhs.id) 
    ssa_rhs = translate_expr(rhs, env)
    return ssa.Assign(ssa_lhs_id, ssa_rhs)
      

  def translate_stmt(stmt, env):
    """
    Given a stmt, dispatch based on its class type to a particular
    translate_ function and return the set of nonlocal vars accessed
    by this statment
    """
    if isinstance(stmt, ast.FunctionDef):
      fundef = translate_FunctionDef(stmt.name, stmt.args, stmt.body)
      nonlocals.update(fundef.nonlocals)
      # update some global table of defined functions? 
      # give the function a unique SSA ID? 
    elif isinstance(stmt, ast.Assign):     
      return translate_Assign(stmt.target[0], stmt.value)
    elif isinstance(stmt, ast.Return):
      return ssa.Return(translate_expr(stmt.value))
  
  
  ssa_body = [translate_stmt(stmt) for stmt in body]
  # should I register the function globally now? 
  return {'body': body, 'nonlocals':nonlocals}
  
  

    
  


def translate_module(m, outer_env = None):
  assert isinstance(m, ast.Module)
  assert len(m.body) == 1
  assert isinstance(m.body[0], ast.FunctionDef)
  return translate_FunctionDef(m.body[0], outer_env)
  