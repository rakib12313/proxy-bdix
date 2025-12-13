
const express = require('express');
const router = express.Router();
const { getUploadSignature, saveFileMetadata, listFiles, deleteFile } = require('../controllers/fileController');
const authenticate = require('../middleware/auth');

// All routes require auth
router.use(authenticate);

router.get('/signature', getUploadSignature);
router.post('/metadata', saveFileMetadata);
router.get('/', listFiles);
router.delete('/:id', deleteFile);

module.exports = router;
