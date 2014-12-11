var API_SONG_SEARCH = 'http://music.163.com/api/search/get/web?csrf_token=';
var API_SONG_DETAIL = 'http://music.163.com/api/song/detail/';

function search(song) {
    alert(song);
    $.ajax({
        type: 'POST',
        url: API_SONG_SEARCH,
        data: {
            type: '1',
            s: song,
            offset: '0',
            limit: '30'
        },
        success: function(data) {
            alert(data);
        },
        error: function() {
            alert('error');
        }
    });
}
