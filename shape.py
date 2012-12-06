from node import Node  

class ValueMismatch(Exception):
  """
  Raise this exception whenever two incompatible
  abstract values get combined
  """
  def __init__(self, v1, v2):
    self.v1 = v1
    self.v2 = v2 

  def __str__(self):
    return "ValueMismatch(%s, %s)" % (self.v1, self.v2)

  def __repr__(self):
    return str(self)
  
  
class AbstractValue(Node):
  pass 

class Unknown(Node):
  def __eq__(self, other):
    return isinstance(other, Unknown)
  
  def combine(self, other):
    return other 
  
  def __str__(self):
    return "<unknown>"
  
  def __repr__(self):
    return str(self)

unknown_value = Unknown()


class Scalar(AbstractValue):
  """
  Base class for all scalar operations
  """
  rank = 0
  
class UnknownScalar(Scalar):
  def __eq__(self, other):
    return isinstance(other, UnknownScalar)
  
  def combine(self, other):
    assert isinstance(other, Scalar), \
      "Can't combine scalar with %s" % other 
    return self 
  
  def __str__(self):
    return "Scalar"
  
unknown_scalar = UnknownScalar()

class Const(Scalar):
  def __init__(self, value):
    self.value = value 
    
  def __eq__(self, other):
    return isinstance(other, Const) and other.value == self.value
    
  def __str__(self):
    return "Const(%d)" % self.value 

  def combine(self, other):
    if self == other:
      return self
    elif isinstance(other, Scalar):
      return unknown_scalar
    else:
      raise ValueMismatch(self, other)

def const(x):
  return Const(x)

def is_zero(d):
  return isinstance(d, Const) and d.value == 0

def is_one(d):
  return isinstance(d, Const) and d.value == 1

class Binop(Scalar):
  def __init__(self, x, y):
    self.x = x 
    self.y = y 
  
  def __eq__(self, other):
    return self.__class__ == other.__class__ and \
      self.x == other.x and \
      self.y == other.y 

  def __repr__(self):
    return str(self) 
  
  def __hash__(self):
    return hash( (self.x, self.y) )


class Sub(Binop):
  def __str__(self):
    return "%s - %s" % (self.x, self.y)
  
class Add(Binop):
  def __str__(self):
    return "%s + %s" % (self.x, self.y)
  
class Div(Binop):
  def __str__(self):
    return "%s / %s" % (self.x, self.y)
  
class Mult(Binop):
  def __str__(self):
    return "%s * %s" % (self.x, self.y)

class Mod(Binop):
  def __str__(self):
    return "%s % %s" % (self.x, self.y)

  
class Var(Scalar):
  def __init__(self, num):
    self.num = num 
    
  def __eq__(self, other):
    return isinstance(other, Var) and self.num == other.num
  
  def __hash__(self):
    return hash(self.num)
  
  def __str__(self):
    return "x%d" % self.num 
  
  def __repr__(self):
    return str(self)
  
  def combine(self, other):
    if self == other:
      return self 
    else:
      # combining two different variables returns an unknown scalar 
      return unknown_scalar 


class Shape(AbstractValue):
  def __init__(self, dims):
    assert len(dims) > 0
    self.dims = [const(d) if isinstance(d, int) else d for d in dims] 
    self.rank = len(dims)
      
  def __eq__(self, other):
    return isinstance(other, Shape) and \
      len(self.dims) == len(other.dims) and \
      all(d1 == d2 for (d1,d2) in zip(self.dims, other.dims) )
  
  def __str__(self):
    return "Shape(%s)" % (", ".join(str(d) for d in self.dims))
  
  def __repr__(self):
    return str(self)
  
  def combine(self, other):
    if isinstance(other, Shape) and other.rank == self.rank:
      dims = combine_pairs(self.dims, other.dims)
      return make_shape(dims)
    raise ValueMismatch(self, other)

def make_shape(dims):
  if len(dims) == 0:
    return unknown_scalar
  return Shape(tuple(dims)) 


def dim(shape, d):
  if isinstance(shape, Shape):
    return shape.dims[d]
  else:
    # if the shape isn't available, getting the d'th 
    # dimension returns an unknown scalar 
    return unknown_scalar 
  
def dim_list(shapes, d, exclude_scalars=False):
  if exclude_scalars:
    shapes = [s for s in shapes if not is_scalar(s)]
  return [dim(s,d) for s in shapes]


def array_of_unknown_shape(rank):
  return Shape([unknown_scalar] * rank)

def lower_rank(x, axis):
  assert isinstance(x, Shape), \
    "Can't decrease rank of %s" % x
  # by convention, lowering a scalar returns a scalar 
  if  axis >= x.rank or x.rank == 1:
    return unknown_scalar

  new_dims = []
  for (i,d) in enumerate(x.dims):
    if i != axis:
      new_dims.append(d)
  return make_shape(new_dims)

def lower_ranks(xs, axis):
  return [lower_rank(x, axis) for x in xs]
    
def increase_rank(x, axis, dim_expr):
  if isinstance(dim_expr, int):
    dim_expr = const(dim_expr)
    
  if isinstance(x, Shape):
    # we're taking dims d1...dm and constructing a 
    # new shape d1...d_new...dm by inserting d_new
    # in the slot of the given axis 
    assert axis <= x.rank 
    if axis < len(x.dims):
      new_dims = []
      for (i,d) in enumerate(x.dims):
        if i == axis:
          new_dims.append(dim_expr)
        new_dims.append(d)
    else:
      new_dims = [d for d in x.dims]
      new_dims.append(dim_expr)
    return make_shape(new_dims)
  elif is_scalar(x):
    return Shape([dim_expr])        
  else:
    raise RuntimeError("Don't know how to raise rank of value %s" % x)
   

def is_scalar(v):
  return isinstance(v, Scalar) 

class Slice(AbstractValue):
  def __init__(self, start, stop, step):
    self.start = start
    self.stop = stop 
    self.step = step 
    
  def __eq__(self, other):
    return isinstance(other, Slice) and \
      self.start == other.start and \
      self.stop == other.stop and \
      self.step == other.step 
  
  def combine(self, other):
    if isinstance(other, Slice):
      start = self.start.combine(other.start)
      stop = self.stop.combine(other.stop)
      step = self.step.combine(other.step)
      return Slice(start, stop, step)
    else:
      raise ValueMismatch(self, other)


class Tuple(AbstractValue):
  def __init__(self, elts):
    self.elts = tuple(elts) 
    
  def __eq__(self, other):
    return isinstance(other, Tuple) and \
      len(self.elts) == len(other.elts) and \
      all(e1 == e2 for (e1, e2) in zip(self.elts, other.elts))
  
  def __len__(self):
    return len(self.elts)
  
  def __iter__(self):
    return iter(self.elts)
  
  def __str__(self):
    return "Tuple(%s)" % ", ".join(str(e) for e in self.elts)
  
  def combine(self, other):
    if isinstance(other, Tuple):
      if len(self.elts) == len(other.elts):
        return Tuple(combine_pairs(self.elts, other.elts))
    raise ValueMismatch(self, other)

class Closure(AbstractValue):
  def __init__(self, fn, args):
    self.fn = fn 
    self.args = args 
  
  def __str__(self):
    return "Closure(fn = %s, %s)" % \
      (self.fn, ", ".join(str(e) for e in self.elts))
  
  def __eq__(self, other):
    return isinstance(other, Closure) and \
      self.fn == other.fn and \
      len(self.arg_shapes) == len(other.arg_shapes) and \
      all(v1 == v2 for (v1,v2) in zip(self.args, other.args))
  
  def combine(self, other):
    if isinstance(other, Closure):
      # TODO: Implement sets of closures like we have in the type system 
      if self.fn == other.fn and \
         len(self.args) == len(other.args):
        combined_args = combine_pairs(self.args, other.args)
        return Closure(self.fn, combined_args)
    raise ValueMismatch(self, other)  


def combine_list(xs, preserve_const = True):
  acc = unknown_value
  for x in xs:
    acc = acc.combine(x)
  if not preserve_const and isinstance(acc, Const):
    acc = unknown_scalar 
  return acc 
    

def combine_pairs(xs, ys):
  return [xi.combine(yi) for (xi, yi) in zip(xs, ys)]

