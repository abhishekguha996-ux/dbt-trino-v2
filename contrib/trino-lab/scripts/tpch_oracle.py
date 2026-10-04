"""Compare materialized dbt outputs with independent Python joins and Decimal sums."""
from collections import defaultdict
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys


def verify(rows, relation_prefix):
    """`rows(sql)` returns result rows; `relation_prefix` is the catalog.schema holding the models."""
    customers={k:(nation,segment) for k,nation,segment in rows('select c_custkey,c_nationkey,c_mktsegment from tpch.tiny.customer')}
    orders={k:(customer,day,priority) for k,customer,day,priority in rows('select o_orderkey,o_custkey,o_orderdate,o_shippriority from tpch.tiny.orders')}
    suppliers=dict(rows('select s_suppkey,s_nationkey from tpch.tiny.supplier'))
    nations={k:(name,region) for k,name,region in rows('select n_nationkey,n_name,n_regionkey from tpch.tiny.nation')}
    regions=dict(rows('select r_regionkey,r_name from tpch.tiny.region'))
    shipping=defaultdict(Decimal)
    regional=defaultdict(Decimal)
    lines=rows('select l_orderkey,l_suppkey,cast(l_extendedprice as decimal(18,2)),cast(l_discount as decimal(4,2)),l_shipdate from tpch.tiny.lineitem')
    for order_key,supplier,price,discount,ship_date in lines:
        customer,order_date,priority=orders[order_key]
        nation,segment=customers[customer]
        nation_name,region=nations[nation]
        revenue=price*(Decimal(1)-discount)
        if segment == 'BUILDING' and order_date < date(1995,3,15) and ship_date > date(1995,3,15):
            shipping[(order_key,order_date,priority)]+=revenue
        if regions[region] == 'ASIA' and date(1994,1,1) <= order_date < date(1995,1,1) and suppliers[supplier] == nation:
            regional[nation_name]+=revenue
    actual_shipping={tuple(row[:3]):row[3] for row in rows(f'select orderkey,orderdate,shippriority,revenue from {relation_prefix}.shipping_revenue')}
    actual_regional=dict(rows(f'select nation,revenue from {relation_prefix}.regional_revenue'))
    assert actual_shipping == dict(shipping), 'Shipping revenue does not match Python oracle'
    assert actual_regional == dict(regional), 'Regional revenue does not match Python oracle'
    assert shipping and regional
    return {'status':'pass','source_line_count':len(lines),'shipping_groups':len(shipping),
            'shipping_total':str(sum(shipping.values())),'regional_groups':len(regional),
            'regional_total':str(sum(regional.values()))}
