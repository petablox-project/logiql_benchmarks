#!/usr/bin/env python3

import argparse
import sys
import os

sys.path.append('python')
sys.path.append('../../apisan/analyzer')

import traces_pb2
from apisan.parse.explorer import Explorer
from apisan.parse.symbol import *
from apisan.parse.event import CallEvent, AssumeEvent

retvar = 0
def get_value():
    global retvar
    x = retvar
    retvar = retvar + 1
    return x

def pb_binop(s):
    if s == '+':
        return 1
    elif s == '*':
        return 2
    elif s == '/':
        return 3
    elif s == '%':
        return 4
    elif s == '-':
        return 5
    elif s == ">>":
        return 6
    elif s == "<<":
        return 7
    elif s == '<':
        return 8
    elif s == "<=":
        return 9
    elif s == ">=":
        return 10
    elif s == ">":
        return 11
    elif s == "==":
        return 12
    elif s == "!=":
        return 13
    elif s == "&":
        return 14
    elif s == "|":
        return 15
    elif s == "^":
        return 16
    elif s == "&&":
        return 17
    elif s == "||":
        return 18
    else:
        raise TypeError(str(s))

def pb_concrete_int(s, exp):
    exp.int_lit = s.value

def pb_concrete_string(s, exp):
    exp.str_lit = s.string

def pb_var(s, exp):
    exp.id = s.id

def pb_binop_expr(s, exp, calls):
    binexpr = traces_pb2.BinopExpr()
    exp_l = traces_pb2.Expression()
    exp_r = traces_pb2.Expression()
    binexpr.binop_l = pb_expr(exp.lhs, exp_l, calls)
    binexpr.binop_r = pb_expr(exp.rhs, exp_r, calls)
    binexpr.binop = pb_binop(exp.op)
    exp.bin = binexpr

def pb_proj_expr(s, exp, calls):
    projexpr = traces_pb2.ProjExpr()
    exp_base = traces_pb2.Expression()
    projexpr.base = pb_expr(exp.base, exp_base, calls)
    projexpr.field = exp.member
    exp.proj = projexpr

def pb_arr_expr(s, exp, calls):
    arrexpr = traces_pb2.ArrayExpr()
    exp_base = traces_pb2.Expression()
    exp_index = traces_pb2.Expression()
    arrexpr.base = pb_expr(exp.base, exp_base, calls)
    arrexpr.index = pb_expr(exp.index, exp_index, calls)
    exp.arr = arrexpr

def pb_call(s, exp, calls):
    exp.ret_var = calls[s]

def pb_expr(s, exp, calls):
    if isinstance(s, ConcreteIntSymbol):
        pb_concrete_int(s, exp)
    elif isinstance(s, StringLiteralSymbol):
        pb_concrete_string(s, exp)
    elif isinstance(s, IDSymbol):
        pb_var(s, exp)
    elif isinstance(s, BinaryOperatorSymbol):
        pb_binop_expr(s, exp, calls)
    elif isinstance(s, FieldSymbol):
        pb_proj_expr(s, exp, calls)
    elif isinstance(s, ArraySymbol):
        pb_array_expr(s, exp, calls)
    elif isinstance(s, CallSymbol):
        pb_call(s, exp, calls)
    else:
        raise TypeError(str(s))


def generate_output(trees, traces):
    calls = {}
    for tree in trees:
        trace = traces.traces.add()
        stack = []
        stack.append(tree.root)
        while stack:
            current = stack.pop()
            if isinstance(current.event, CallEvent):
                event = trace.events.add()
                call = current.event
            
                call_event = event.call_event
                call_event.name = call.call.name.id

                if not (call.call in calls):
                    print(call.call)
                    next_id = get_value()
                    calls[call.call] = next_id

                call_event.retid = calls[call.call]

                for arg in call.call.args:
                    exp = call_event.args.add()
                    pb_expr(arg, exp, calls)

            elif isinstance(current.event, AssumeEvent):
                event = trace.events.add()
                cons = current.event
            
                cons_event = event.check_event
                to_check = traces_pb2.Expression()
                pb_expr(cons.cond.symbol, cons_event.checked, calls)

                for r in cons.cond.constraints:
                    rng = cons_event.ranges.ranges.add()
                    rng.min = r[0]
                    if r[1] > 9223372036854775807:
                        rng.max = 9223372036854775807
                    else:
                        rng.max = r[1]

            stack.extend(current.children)

        # In other cases we don't materialize the check in the representation


def main():
    explorer = Explorer(None)
    traces = traces_pb2.Traces()
    for f in sys.argv[1:]:
        trees = explorer._parse_file(f)
        generate_output(trees, traces)
        
    out_file = open('data.protoout', 'wb')
    out_file.write(traces.SerializeToString())
    out_file.close()

if __name__ == "__main__":
    main()
