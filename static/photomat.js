// state: 0 ready to take picture, 1 taking picture, 2 showing picture, 3 printing picture
state = 0;

$(document).ready(function() {
    // On vérifie régulièrement si on peut prendre une photo
    // i.e. le dossier pending_pictures est vide
    $('#content').html('Le photomaton est prêt!');
    loopCheck = setInterval(checkState, 500);
});

function checkState() {
    $.get('/state/', function(data) {
        json = JSON.parse(data);
        newState = parseInt(json.state);
        if (newState != state) {
            if (newState == 0) {
                $('#content').html('Le photomaton est prêt!');
            } else if (newState == 1) {
                $('#content').html('Photo est en cours...');
            } else if (newState == 2) {
                last_picture = json.last_picture
                $('#content').html('Voici votre photo: <img src="' + last_picture + '"></img>')
            } else if (newState == 3) {
                $('#content').html('Photo est en impression...');
            }
        }
        state = newState;
    });
}