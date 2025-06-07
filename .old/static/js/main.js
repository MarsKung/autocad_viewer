document.addEventListener('DOMContentLoaded', () => {
    // DOM Element Selectors
    const userProfileDiv = document.getElementById('user-profile');
    const hubsList = document.getElementById('hubs-list');
    const projectsList = document.getElementById('projects-list');
    const foldersList = document.getElementById('folders-list');
    const itemsList = document.getElementById('items-list');
    const uploadForm = document.getElementById('upload-form');
    const uploadStatus = document.getElementById('upload-status');
    const uploadTargetFolder = document.getElementById('upload-target-folder');
    const viewerDiv = document.getElementById('viewerDiv');
    let viewer;
    let selectedFolderId = null;

    // Helper to clear and message a list
    function setListMessage(listElement, message) {
        listElement.innerHTML = `<li style="cursor: default; color: #777;">${message}</li>`;
    }

    // --- Data Fetching Functions ---
    async function fetchAndDisplay(url, listElement, itemRenderer) {
        setListMessage(listElement, '載入中...');
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const result = await response.json();
            
            listElement.innerHTML = '';
            if (result.data.length === 0) {
                setListMessage(listElement, '沒有項目。');
                return;
            }
            result.data.forEach(item => listElement.appendChild(itemRenderer(item)));
        } catch (error) {
            console.error(`Failed to fetch from ${url}:`, error);
            setListMessage(listElement, '載入失敗。');
        }
    }

    // --- Item Rendering Functions ---
    const createHubListItem = (hub) => {
        const li = document.createElement('li');
        li.textContent = hub.attributes.name;
        li.dataset.id = hub.id;
        li.dataset.type = 'hub';
        return li;
    };

    const createProjectListItem = (project) => {
        const li = document.createElement('li');
        li.textContent = project.attributes.name;
        li.dataset.id = project.id;
        li.dataset.type = 'project';
        return li;
    };

    const createFolderListItem = (folder) => {
        const li = document.createElement('li');
        li.textContent = `📁 ${folder.attributes.displayName}`;
        li.dataset.id = folder.id;
        li.dataset.type = 'folder';
        return li;
    };

    const createItemListItem = (item) => {
        const li = document.createElement('li');
        li.textContent = `📄 ${item.attributes.displayName}`;
        // The URN for the viewer is the base64 encoded version of the version's ID
        // We need the tip version id from the relationships
        if(item.relationships.tip.data) {
             const versionId = item.relationships.tip.data.id;
             li.dataset.urn = btoa(versionId).replace(/=/g, '');
        }
        li.dataset.type = 'item';
        return li;
    };

    // --- Event Listeners ---
    hubsList.addEventListener('click', e => {
        if (!e.target || e.target.dataset.type !== 'hub') return;
        const hubId = e.target.dataset.id;
        document.querySelectorAll('#hubs-list li').forEach(li => li.classList.remove('active'));
        e.target.classList.add('active');
        
        // Clear subsequent lists
        setListMessage(projectsList, ''); setListMessage(foldersList, ''); setListMessage(itemsList, '');
        uploadForm.style.display = 'none';
        uploadStatus.textContent = '請先在上方選擇一個資料夾';

        fetchAndDisplay(`/api/hubs/${hubId}/projects`, projectsList, createProjectListItem);
    });

    projectsList.addEventListener('click', e => {
        if (!e.target || e.target.dataset.type !== 'project') return;
        const projectId = e.target.dataset.id;
        document.querySelectorAll('#projects-list li').forEach(li => li.classList.remove('active'));
        e.target.classList.add('active');

        setListMessage(foldersList, ''); setListMessage(itemsList, '');
        uploadForm.style.display = 'none';
        uploadStatus.textContent = '請先在上方選擇一個資料夾';

        fetchAndDisplay(`/api/projects/${projectId}/top-folders`, foldersList, createFolderListItem);
    });

    foldersList.addEventListener('click', e => {
        if (!e.target || e.target.dataset.type !== 'folder') return;
        selectedFolderId = e.target.dataset.id;
        document.querySelectorAll('#folders-list li').forEach(li => li.classList.remove('active'));
        e.target.classList.add('active');
        
        uploadTargetFolder.textContent = e.target.textContent;
        uploadForm.style.display = 'block';
        uploadStatus.textContent = '可以選擇檔案上傳了。';

        fetchAndDisplay(`/api/folders/${selectedFolderId}/contents`, itemsList, createItemListItem);
    });
    
    itemsList.addEventListener('click', e => {
        if (!e.target || e.target.dataset.type !== 'item') return;
        const urn = e.target.dataset.urn;
        if (urn) {
            document.querySelectorAll('#items-list li').forEach(li => li.classList.remove('active'));
            e.target.classList.add('active');
            launchViewer(urn);
        } else {
            alert('此項目沒有可供檢視的版本。');
        }
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('modelFile');
        if (fileInput.files.length === 0 || !selectedFolderId) {
            alert('請選擇檔案和目標資料夾');
            return;
        }
        
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('modelFile', file);

        const submitButton = uploadForm.querySelector('button');
        submitButton.disabled = true;
        uploadStatus.textContent = `正在上傳 ${file.name}，請稍候... (此過程可能需要一些時間)`;

        try {
            const response = await fetch(`/api/folders/${selectedFolderId}/upload`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (!response.ok) {
                const detailError = result.errors && result.errors[0] ? result.errors[0].detail : (result.error || '上傳失敗，未知錯誤。');
                throw new Error(detailError);
            }
            
            uploadStatus.textContent = `✅ ${result.message}`;
            setTimeout(() => {
                // Refresh the folder contents after successful upload
                document.querySelector('#folders-list li.active')?.click();
                uploadStatus.textContent = '可以選擇檔案上傳了。';
                submitButton.disabled = false;
                uploadForm.reset();
            }, 3000);

        } catch (error) {
            uploadStatus.textContent = `❌ 上傳失敗: ${error.message}`;
            console.error('上傳失敗:', error);
            submitButton.disabled = false;
        }
    });

    // --- Viewer Logic ---
    async function launchViewer(urn) {
        try {
            const tokenResp = await fetch('/api/auth/token');
            const tokenData = await tokenResp.json();
            if (!tokenResp.ok) throw new Error(tokenData.error);
            
            const options = {
                env: 'AutodeskProduction',
                accessToken: tokenData.access_token,
            };

            const BROWSER_IS_WEBGL_COMPATIBLE = Autodesk.Viewing.isWebGLSupported();
            if (!BROWSER_IS_WEBGL_COMPATIBLE) {
                alert('您的瀏覽器不支援 WebGL，無法顯示模型。');
                return;
            }

            if (viewer && viewer.running) {
                // If viewer is already running, just load new model
                viewer.loadDocument('urn:' + urn, onDocumentLoadSuccess, onDocumentLoadFailure);
            } else {
                Autodesk.Viewing.Initializer(options, () => {
                    viewer = new Autodesk.Viewing.GuiViewer3D(viewerDiv);
                    viewer.start();
                    Autodesk.Viewing.Document.load('urn:' + urn, onDocumentLoadSuccess, onDocumentLoadFailure);
                });
            }

        } catch (error) {
            alert(`無法載入 Viewer: ${error.message}`);
            console.error(error);
        }
    }

    function onDocumentLoadSuccess(doc) {
        const viewables = doc.getRoot().getDefaultGeometry();
        viewer.loadDocumentNode(doc, viewables).then(() => {
            console.log(`模型載入成功`);
        });
    }

    function onDocumentLoadFailure(viewerErrorCode, errorMsg) {
        console.error(`載入模型失敗`, viewerErrorCode, errorMsg);
        alert('載入此模型失敗，它可能仍在雲端轉換中，或轉換失敗。');
    }

    // --- Initial Load ---
    fetch('/api/user/profile')
        .then(response => response.ok ? response.json() : Promise.reject(response))
        .then(user => {
            userProfileDiv.textContent = `使用者: ${user.firstName} ${user.lastName}`;
            fetchAndDisplay('/api/hubs', hubsList, createHubListItem);
        }).catch(() => {
            userProfileDiv.textContent = '獲取使用者資訊失敗';
            setListMessage(hubsList, '');
        });
});