// state: 0 ready to take picture, 1 taking picture, 2 showing picture, 3 printing picture
state = -1;

$(document).ready(function() {
    // On vérifie régulièrement si on peut prendre une photo
    // i.e. le dossier pending_pictures est vide
    loopCheck = setInterval(checkState, 500);
});

function checkState() {
    $.get('/state/', function(data) {
        json = JSON.parse(data);
        newState = parseInt(json.state);
        if (newState != state) {
            $("#content").html(json.html);
        }
        state = newState;
    });
}