/* =====================================================================
   SRET date reading (Matt, 2026-09-28). One engine for every import: the
   grid's milestone import and, at merge, the dashboard's schedule import.
   No UI, no app globals.

   A sheet's dates arrive as whatever the author typed or Excel exported:
   9-Oct-26, 2026-10-09, 09/10/26, 10.09.2026, 9 October 2026, an Excel
   serial. Numeric dates are ambiguous, so the order is worked out from all
   the values of a file together, before any single value is read:

     - Split each value on any break: - / . space or comma.
     - A four-digit first part is a year (year first). A four-digit last part
       is a year (year last).
     - A part above 12 cannot be a month: above 12 first means day first;
       above 12 in the middle means month first.
     - A part above 31 can only be a year.
     - An order that makes any value an impossible date is dropped.
     - If several orders still fit, the part that barely changes is the year
       (a sheet's dates span months, so e.g. every value starting 26 means
       year first).
     - Still undecided: day first (the default), marked as not confirmed.

   API (window.SRETDates):
     detect(values)          -> {order:'DMY'|'MDY'|'YMD', confirmed, reason, numeric, ambiguous}
     parse(v, order)         -> {ok:true, value:'YYYY-MM-DD'|null} | {ok:false}
     orderLabel(order)       -> 'day/month/year' ...
     example(order)          -> '9/10/26 is 9-Oct-26' ...
   Two-digit years are 20yy, the rule the app already uses.
   ===================================================================== */
(function(root){
  'use strict';
  var MONTHS=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
  var ORDERS=['DMY','YMD','MDY'];   // preference when nothing else decides
  var LABEL={DMY:'day/month/year',MDY:'month/day/year',YMD:'year/month/day'};

  function pad(n){ return String(n).padStart(2,'0'); }
  function iso(y,m,d){ return y+'-'+pad(m)+'-'+pad(d); }
  function valid(y,m,d){
    if(!(m>=1&&m<=12&&d>=1&&d<=31)) return false;
    var dt=new Date(Date.UTC(y,m-1,d));
    return dt.getUTCFullYear()===y&&dt.getUTCMonth()===m-1&&dt.getUTCDate()===d;
  }
  function year(t){ var y=+t; return t.length<=2?2000+y:y; }
  function monthOf(t){
    var i=MONTHS.indexOf(String(t).slice(0,3).toLowerCase());
    return i>=0&&/^[a-z]+\.?$/i.test(t)?i+1:0;
  }
  // A trailing time (P6 and Excel exports carry one) is not part of the date.
  function clean(v){
    return String(v).replace(/\s+/g,' ').trim()
      .replace(/[ T]\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?(\s*[AaPp][Mm])?(Z|[+-]\d{2}:?\d{2})?$/,'').trim();
  }
  // What kind of value this is, and its three parts.
  function shape(v){
    if(v==null||v==='') return {kind:'blank'};
    if(v instanceof Date) return isNaN(v)?{kind:'bad'}:{kind:'date',d:v};
    var s=clean(v);
    if(!s) return {kind:'blank'};
    if(/^\d{5}(\.\d+)?$/.test(s)) return {kind:'serial',n:+s};
    if(/^\d{8}$/.test(s)) return {kind:'num',p:[s.slice(0,4),s.slice(4,6),s.slice(6,8)]};
    var p=s.split(/[-\/.,\s]+/).filter(Boolean);
    if(p.length!==3) return {kind:'bad'};
    if(p.every(function(x){ return /^\d{1,4}$/.test(x); })) return {kind:'num',p:p};
    // Month written as a word, in any position: 9 Oct 26, Oct 9 2026, 2026-Oct-09.
    for(var i=0;i<3;i++){
      var m=monthOf(p[i]);
      if(m){
        var rest=p.filter(function(_,j){ return j!==i; });
        if(!rest.every(function(x){ return /^\d{1,4}$/.test(x); })) return {kind:'bad'};
        var y,d;
        if(rest[0].length===4){ y=rest[0]; d=rest[1]; }
        else { d=rest[0]; y=rest[1]; }
        return {kind:'named',y:year(y),m:m,d:+d};
      }
    }
    return {kind:'bad'};
  }
  function byOrder(p,order){
    var y,m,d;
    if(order==='YMD'){ y=p[0]; m=p[1]; d=p[2]; }
    else if(order==='MDY'){ m=p[0]; d=p[1]; y=p[2]; }
    else { d=p[0]; m=p[1]; y=p[2]; }
    // A four-digit part is a year wherever the order says the year is.
    if(y.length===3||m.length>2||d.length>2) return null;
    return {y:year(y),m:+m,d:+d};
  }
  function fits(p,order){ var r=byOrder(p,order); return !!r&&valid(r.y,r.m,r.d); }

  function detect(values){
    var nums=[];
    // A four-digit first part (2026-10-09, 20261009) reads one way only, so it
    // does not vote; the order is about the values that could be misread.
    (values||[]).forEach(function(v){ var s=shape(v); if(s.kind==='num'&&s.p[0].length!==4) nums.push(s.p); });
    var out={order:'DMY',confirmed:false,reason:'',numeric:nums.length,ambiguous:0};
    if(!nums.length){ out.confirmed=true; out.reason='Every date reads one way only.'; return out; }
    // Orders that read every numeric value as a real date.
    var ok=ORDERS.filter(function(o){ return nums.every(function(p){ return fits(p,o); }); });
    var why='', mixed=false;
    if(!ok.length){ mixed=true;
      // Mixed or broken file: keep the order that reads the most values.
      var best=ORDERS.map(function(o){ return [o,nums.filter(function(p){ return fits(p,o); }).length]; })
        .sort(function(a,b){ return b[1]-a[1]; });
      ok=[best[0][0]];
      why='Not every date fits one order; '+best[0][1]+' of '+nums.length+' fit '+LABEL[best[0][0]]+'.';
    } else if(ok.length===1){
      why=reasonFor(ok[0],nums);
    }
    if(ok.length>1){
      // Year position: the part that barely changes across the file.
      var distinct=[0,1,2].map(function(i){ var s={}; nums.forEach(function(p){ s[+p[i]]=1; }); return Object.keys(s).length; });
      var yearFirst=ok.indexOf('YMD')>=0, yearLast=ok.indexOf('DMY')>=0||ok.indexOf('MDY')>=0;
      if(yearFirst&&yearLast&&nums.length>=3&&distinct[0]!==distinct[2]){
        if(distinct[0]<distinct[2]){ ok=['YMD']; why='The first part barely changes ('+distinct[0]+' value'+(distinct[0]===1?'':'s')+'), so it is the year.'; }
        else ok=ok.filter(function(o){ return o!=='YMD'; });
      }
    }
    if(ok.length>1){
      out.order=ok.indexOf('DMY')>=0?'DMY':ok[0];
      out.reason='Nothing in the file settles the order; '+LABEL[out.order]+' is assumed.';
      out.ambiguous=nums.filter(function(p){
        return ok.some(function(o){ var a=byOrder(p,o), b=byOrder(p,out.order); return a&&b&&valid(a.y,a.m,a.d)&&iso(a.y,a.m,a.d)!==iso(b.y,b.m,b.d); });
      }).length;
      out.confirmed=out.ambiguous===0;
      if(out.confirmed) out.reason='Every date reads the same either way.';
      return out;
    }
    out.order=ok[0];
    out.confirmed=!mixed;
    out.reason=why||reasonFor(ok[0],nums);
    return out;
  }
  function reasonFor(order,nums){
    if(order==='DMY'&&nums.some(function(p){ return +p[0]>12; })) return 'A first part above 12 is a day.';
    if(order==='MDY'&&nums.some(function(p){ return +p[1]>12; })) return 'A middle part above 12 is a day.';
    return 'Only '+LABEL[order]+' reads every date.';
  }

  function parse(v,order){
    var s=shape(v);
    if(s.kind==='blank') return {ok:true,value:null};
    if(s.kind==='date') return {ok:true,value:iso(s.d.getUTCFullYear(),s.d.getUTCMonth()+1,s.d.getUTCDate())};
    if(s.kind==='serial'){
      if(s.n<20000||s.n>80000) return {ok:false};
      var d=new Date(Date.UTC(1899,11,30)+Math.floor(s.n)*86400000);
      return {ok:true,value:iso(d.getUTCFullYear(),d.getUTCMonth()+1,d.getUTCDate())};
    }
    if(s.kind==='named') return valid(s.y,s.m,s.d)?{ok:true,value:iso(s.y,s.m,s.d)}:{ok:false};
    if(s.kind==='num'){
      // A four-digit first part is always year first, whatever the file order.
      var r=byOrder(s.p,s.p[0].length===4?'YMD':(order||'DMY'));
      return r&&valid(r.y,r.m,r.d)?{ok:true,value:iso(r.y,r.m,r.d)}:{ok:false};
    }
    return {ok:false};
  }
  function orderLabel(o){ return LABEL[o]||LABEL.DMY; }
  function example(o){
    return {DMY:'9/10/26 is 9-Oct-26',MDY:'10/9/26 is 9-Oct-26',YMD:'26/10/9 is 9-Oct-26'}[o]||'';
  }

  root.SRETDates={detect:detect,parse:parse,orderLabel:orderLabel,example:example,ORDERS:ORDERS.slice()};
})(window);
