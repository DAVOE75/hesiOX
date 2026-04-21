document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.zoomable-img').forEach(function(img) {
        img.addEventListener('click', function() {
            let modal = document.createElement('div');
            modal.className = 'zoom-modal';
            modal.innerHTML = `
                <div class="zoom-modal-bg"></div>
                <div class="zoom-modal-content">
                    <img src="${img.src}" class="img-fluid" style="max-width:90vw; max-height:90vh;">
                </div>
            `;
            document.body.appendChild(modal);
            modal.querySelector('.zoom-modal-bg').onclick = function() {
                document.body.removeChild(modal);
            };
        });
    });
});
