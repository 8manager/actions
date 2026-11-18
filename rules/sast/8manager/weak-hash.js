const crypto = require('crypto');
import { createHash } from 'node:crypto';
// ruleid: weak-hash
const a = crypto.createHash('md5').update(x).digest('hex');
// ruleid: weak-hash
const b = createHash("sha1").update(x).digest('hex');
// ok: weak-hash
const c = createHash('sha256').update(x).digest('hex');
