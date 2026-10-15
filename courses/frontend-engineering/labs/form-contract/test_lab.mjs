import test from 'node:test';
import assert from 'node:assert/strict';
import { validateEnrollment, renderStatus } from './form.mjs';
const valid = { email:'learner@example.test', plan:'foundation', acceptedTerms:true };
test('accepts correctly scoped input',()=>assert.equal(validateEnrollment(valid).ok,true));
test('rejects missing agreement',()=>assert.equal(validateEnrollment({...valid,acceptedTerms:false}).ok,false));
test('rejects unknown plan',()=>assert.equal(validateEnrollment({...valid,plan:'enterprise-admin'}).ok,false));
test('rejects mass assignment fields',()=>assert.equal(validateEnrollment({...valid,isAdmin:true}).ok,false));
test('rejects invalid emails',()=>assert.equal(validateEnrollment({...valid,email:'malformed'}).ok,false));
test('renders untrusted text without HTML parsing',()=>{
 const node={textContent:''};const text='<img src=x onerror=alert(1)>';
 renderStatus(node,text);assert.equal(node.textContent,text);
});
