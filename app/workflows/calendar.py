"""Bounded timezone-aware schedule calculation, using UTC instants across DST."""
import re
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo

def cron_fields(expression):
 parts=expression.split()
 if len(parts)!=5 or not re.fullmatch(r'[0-9*/ ,\-]+',expression):raise ValueError('Use five numeric cron fields.')
 fields=[]
 for part,low,high in zip(parts,(0,0,1,1,0),(59,23,31,12,6)):
  values=set()
  for segment in part.split(','):
   base,_,step=segment.partition('/');step=int(step or 1)
   if step<1 or step>high+1:raise ValueError('Invalid cron step')
   a,b=(low,high) if base=='*' else tuple(map(int,base.split('-',1))) if '-' in base else (int(base),int(base))
   if not low<=a<=b<=high:raise ValueError('Cron value is outside its range')
   values.update(range(a,b+1,step))
  fields.append(values)
 return parts,fields

def next_due(config,after=None):
 after=after or datetime.now(timezone.utc)
 start=datetime.fromisoformat(config['start_at'].replace('Z','+00:00'))
 if start.tzinfo is None:raise ValueError('Start time needs a timezone offset.')
 zone=ZoneInfo(config['timezone']);frequency=config['frequency']
 if frequency=='once':return start.astimezone(timezone.utc).isoformat() if start>after else None
 if frequency=='custom':parts,fields=cron_fields(config.get('cron_expression') or '')
 else:
  local=start.astimezone(zone);parts=['*']*5;fields=[{local.minute},{local.hour},set(range(1,32)),set(range(1,13)),set(range(7))]
  if frequency=='weekdays':fields[4]={1,2,3,4,5}
  if frequency=='weekly':fields[4]={(local.weekday()+1)%7}
 instant=max(after,start-timedelta(minutes=1)).astimezone(timezone.utc).replace(second=0,microsecond=0)+timedelta(minutes=1)
 for _ in range(527040):
  local=instant.astimezone(zone);values=(local.minute,local.hour,local.day,local.month,(local.weekday()+1)%7)
  match=[v in f for v,f in zip(values,fields)]
  # Conventional cron OR semantics when both day fields are restricted.
  daymatch=(match[2] or match[4]) if frequency=='custom' and parts[2]!='*' and parts[4]!='*' else match[2] and match[4]
  if match[0] and match[1] and match[3] and daymatch:return instant.isoformat()
  instant+=timedelta(minutes=1)
 raise ValueError('No occurrence found within one year.')
