/* Helpers for handlebars */

function registHelpers() {
	Handlebars.registerHelper("formatTime", millisecondsToTime);
}

function millisecondsToTime(milli) {
	function addZero(n) {
		return (n < 10 ? '0' : '') + n;
	}
	var seconds = Math.floor((milli / 1000) % 60);
	var minutes = Math.floor((milli / 60000) % 60);
	return addZero(minutes) + ":" + addZero(seconds);
}

/* Navbar refresh */

function refreshNav() {
	cur = $(location).attr('pathname');
	$('.nav-main>li').removeClass('active');
	if (cur.indexOf('/playlist') >= 0) {
		$('.nav-main>li:nth(1)').addClass('active');
	} else {
		$('.nav-main>li:nth(0)').addClass('active');
	}
	$('.navbar input[name=s]').val('');
}

/* Playlist in player */

// function loadSongs() {
// 	$.get('/mine', function(data) {
// 		refreshSongs(data);
// 	});
// }

// function refreshSongs(data) {
// 	if (data['ret'] == 1) {
// 		var playlist = data['people']['player']['playlist'];
// 		if (playlist.length > 0) {
// 			var template = Handlebars.compile($("#player-playlist-template").html());
// 			$('#player-playlist').html(template({'playlist': playlist}));
// 			$('#song-img').attr('src', playlist[0]['img']);
// 			$('div.sm2-playlist-target').html('<ul class="sm2-playlist-bd"><li>' + playlist[0]['name'] + ' - ' + playlist[0]['artist_name'] + '</li></ul>');
// 			$('#player-playlist>li:first').addClass('selected');
// 		} else {
// 			$('#player-playlist').html('<li><a href="javascript:void(0);"></a></li>');
// 			$('#song-img').attr('src', $('#data-logo-img').attr('value'));
// 			$('div.sm2-playlist-target').html('<ul class="sm2-playlist-bd"><li></li></ul>');
// 		}
// 		$('#song-num').html(playlist.length);
// 		deleteSongListener();
// 		clearSongListener();
// 	} else {

// 	}
// }

function refreshSongs(data) {
	$.pjax.reload('#player')
}

function deleteSongListener() {
	$('.delete-song').click(function() {
		data = { 'sids': JSON.stringify([$(this).attr('song-id')]) };
		if ($('div.sm2-bar-ui').hasClass('playing')) {
			if ($('li.selected span').attr('song-id') == $(this).attr('song-id')) {
				var evt = $.Event('click');
				evt.target = $('a.sm2-inline-button').get(0);
				globalActions.play(evt);
			}
		}
		$.post('/api/v1/player/playlist/delete', data, function(data) {
			refreshSongs(data);
		});
	});
}

function clearSongListener() {
	$('.clear-song').click(function() {
		if ($('div.sm2-bar-ui').hasClass('playing')) {
			var evt = $.Event('click');
			evt.target = $('a.sm2-inline-button').get(0);
			globalActions.play(evt);
		}
		$.post('/api/v1/player/playlist/clear', function(data) {
			refreshSongs(data);
		});
	});
}

/* Listeners */

function addSongListener() {
	$('.add-song').click(function() {
		var span = $(this).find('span:first');
		data = {
			'songs': JSON.stringify([{
				'sid': span.attr('song-id'),
				'name': span.attr('song-name'),
				'source': span.attr('song-source'),
				'img': span.attr('song-img'),
				'time': span.attr('song-time'),
				'artist_id': span.attr('song-artist-id'),
				'artist_name': span.attr('song-artist-name')
			}])
		};
		$.post('/api/v1/player/playlist/add', data, (function(sid) {
			return function(data) {
				refreshSongs(data);
				globalPlayLink($('span[song-id=' + sid + ']').prev().get(0));
			}
		})(span.attr('song-id')));
	});
}

function replaceSongListener() {
	$('.replace-song').click(function() {
		songs = [];
		$('.add-song').each(function() {
			var span = $(this).find('span:first');
			songs.push({
				'sid': span.attr('song-id'),
				'name': span.attr('song-name'),
				'source': span.attr('song-source'),
				'img': span.attr('song-img'),
				'time': span.attr('song-time'),
				'artist_id': span.attr('song-artist-id'),
				'artist_name': span.attr('song-artist-name')
			});
		});
		data = { 'songs': JSON.stringify(songs) };
		$.post('/api/v1/player/playlist/replace', data, function(data) {
			refreshSongs(data);
			globalPlayLink($('li.selected a').get(0));
		});
	});
}

function connectRequestListener() {
	$('.connectRequestButton').click(function() {
		sendMsg($(this).attr('data-pid'), 1);
	});
}

/* Auto reload */

function autoReload() {
	refreshNav();
	addSongListener();
	replaceSongListener();
	connectRequestListener();
}

/* Pjax */

function pjaxListener(callback) {
	$.pjax.defaults.timeout = false
	$(document).pjax('a[data-pjax]');
	$(document).on('pjax:complete', function() {
		callback();
	});
	$(document).on('submit', 'form[data-pjax]', function(event) {
		$.pjax.submit(event)
	});
}

/* WebSocket */

var ws;

function connectWebSocket() {
	ws = new WebSocket('ws://' + $('#data-ws-host').attr('value') + ':' + $('#data-ws-port').attr('value'));
	ws.onopen = function () {
		ws.send(JSON.stringify({'from':$('#data-pid').attr('value')}));
	};
	ws.onmessage = function (e) {
		console.log('server: ' + e.data);
		var msg = $.parseJSON(e.data);
		if (msg.content === 1) {
			$('#connectRequestModal').modal();
		}
	};
}

function sendMsg(to, content) {
	ws.send(JSON.stringify({
		'from': $('#data-pid').attr('value'),
		'to': to,
		'content': content
	}));
}

/* Onload */

$(function() {
	registHelpers();
	// loadSongs();
	autoReload();
	pjaxListener(autoReload);
	// connectWebSocket();
});
