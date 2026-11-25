'use strict';
const fs=require('fs');const vm=require('vm');const path=require('path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'receiver/standalone/js/network_guard.js'),'utf8');
const attempts=[];const context={globalThis:null,navigator:{sendBeacon(){return true;}},document:{getElementById(){return null;},createElement(){return {style:{},};},body:{prepend(){}}},console:{error(){}},Promise,TypeError,Error,Date,String};context.globalThis=context;vm.runInNewContext(source,context);
if(!context.networkSelfTest().pass)throw new Error('network guard had boot attempts');
const result=vm.runInNewContext("(()=>{try{new XMLHttpRequest()}catch(e){};try{new WebSocket('ws://blocked')}catch(e){};try{new EventSource('event')}catch(e){};navigator.sendBeacon('x','y');return __networkAttempts.length})()",context);
if(result!==4)throw new Error('expected four blocked attempts, got '+result);
process.stdout.write('network guard blocked all four simulated channels; zero boot attempts\n');
