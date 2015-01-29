/* Entry */

$(function() {
	registHelpers();
	loadSongs();
	autoReload();
	pjaxListener(autoReload);
	// connectWebSocket();
});



/* Helpers */

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



/* Listeners */

function autoReload() {
	refreshNav();
	menuListener();
	addSongListener();
	replaceSongListener();
	connectRequestListener();
}

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

function menuListener() {
	var KEYCODE_ESC = 27;
	$(document).keyup(function(e) {
		if (e.keyCode == KEYCODE_ESC && $('div.sm2-bar-ui').hasClass('playlist-open')) {
			globalActions.menu();
		}
	});
	$(document).on('click', function(e) {
		var playlist = $('div.sm2-playlist-wrapper')[0];
		var control = $('div.sm2-main-controls')[0];
		var target = e.target;
		if (!isDescendant(playlist, target) && !isDescendant(control, target) && $('div.sm2-bar-ui').hasClass('playlist-open')) {
			globalActions.menu();
		}
	});
}

function isDescendant(parent, child) {
	var node = child;
	while (node != null) {
		if (node == parent) {
			return true;
		}
		node = node.parentNode;
	}
	return false;
}

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



/* Player related */

function loadSongs() {
	$.get('/player', function(data) {
		refreshSongs(data);
	});
}

function refreshSongs(data) {
	var song = data['player']['song'];
	var playlist = data['player']['playlist'];
	if (playlist.length > 0) {
		var template = Handlebars.compile($("#player-playlist-template").html());
		$('#player-playlist').html(template({'playlist': playlist}));
		$('#song-name').html(song['name']);
		addLyric(song['id']);
		$('#song-img').attr('src', song['img']);
		$('div.sm2-playlist-target').html('<ul class="sm2-playlist-bd"><li>' + song['name'] + ' - ' + song['artist']['name'] + '</li></ul>');
		$('#player-playlist>li:first').addClass('selected');
	} else {
		$('#player-playlist').html('<li><a href="javascript:void(0);"></a></li>');
		$('#song-img').attr('src', $('#data-logo-img').attr('value'));
		$('div.sm2-playlist-target').html('<ul class="sm2-playlist-bd"><li></li></ul>');
	}
	$('#song-num').html(playlist.length);
	deleteSongListener();
	clearSongListener();
}

function addLyric(sid) {
	$.get('/lyrics/' + sid, function(data) {
		var template = Handlebars.compile($("#song-lyrics-template").html());
		$('#song-lyrics').html(template({'lyrics': data['lyrics']}));
	});
}

function addSongListener() {
	$('.add-song').click(function() {
		var span = $(this).find('span:first');
		data = { 'sid': span.attr('song-id') };
		$.post('/player/playlist', data, (function(sid) {
			return function(data) {
				if (data['ret'] == 1) {
					refreshSongs(data);
					globalPlayLink($('span[song-id=' + sid + ']').prev().get(0));
				}
			}
		})(span.attr('song-id')));
	});
}

function replaceSongListener() {
	$('.replace-song').click(function() {
		sids = [];
		$('.add-song').each(function() {
			var span = $(this).find('span:first');
			sids.push(span.attr('song-id'));
		});
		$.ajax({
			type: "PUT",
			url: "/player/playlist",
			data: {'sids': JSON.stringify(sids)}
		}).done(function(data) {
			if (data['ret'] == 1) {
				refreshSongs(data);
				globalPlayLink($('li.selected a').get(0));
			} else {
			}
		});
	});
}

function deleteSongListener() {
	$('.delete-song').click(function() {
		if ($('div.sm2-bar-ui').hasClass('playing')) {
			if ($('li.selected span').attr('song-id') == $(this).attr('song-id')) {
				var evt = $.Event('click');
				evt.target = $('a.sm2-inline-button').get(0);
				globalActions.play(evt);
			}
		}
		$.ajax({
			type: "DELETE",
			url: "/player/playlist/" + $(this).attr('song-id')
		}).done(function(data) {
			if (data['ret'] == 1) {
				refreshSongs(data);
			} else {
			}
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
		$.ajax({
			type: "DELETE",
			url: "/player/playlist"
		}).done(function(data) {
			if (data['ret'] == 1) {
				refreshSongs(data);
			} else {
			}
		});
	});
}



/* Friend related */

function connectRequestListener() {
	$('.connectRequestButton').click(function() {
		sendMsg($(this).attr('data-pid'), 1);
	});
}



/* WebSocket related */

var ws;

function connectWebSocket() {
	ws = new WebSocket('ws://' + $('#data-ws-host').attr('value') + ':' + $('#data-ws-port').attr('value'));
	ws.onopen = function () {
		ws.send(JSON.stringify({'from':$('#data-pid').attr('value')}));
	};
	ws.onmessage = function (e) {
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

