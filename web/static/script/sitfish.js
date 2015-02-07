/* Entry */

$(function() {
	registHelpers();
	loadSongs();
	autoReload();
	pjaxListener(autoReload);
	toggleListener();
	menuListener();
	connectWebSocket();
});

function registHelpers() {
	Handlebars.registerHelper("formatTime", millisecondsToTime);
}

function loadSongs() {
	$.get('/player', function(data) {
		refreshSongs(data);
	});
}

function autoReload() {
	refreshNav();
	addSongListener();
	replaceSongListener();
	friendRequestListener();
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


/* Helpers */

function millisecondsToTime(milli) {
	function addZero(n) {
		return (n < 10 ? '0' : '') + n;
	}
	var seconds = Math.floor((milli / 1000) % 60);
	var minutes = Math.floor((milli / 60000) % 60);
	return addZero(minutes) + ":" + addZero(seconds);
}


/* Auto Reload */

function refreshNav() {
	cur = $(location).attr('pathname');
	$('.nav-main>li').removeClass('active');
	if (cur.indexOf('/playlist') >= 0) {
		$('.nav-main>li:nth(1)').addClass('active');
	} else {
		$('.nav-main>li:nth(0)').addClass('active');
	}
	$('.navbar input[name=s]').val('');
	refreshNotice();
}

function refreshNotice() {
	$.get('/requests', function(data) {
		var num = data.receive.length;
		$('#notice').html(num > 0 ? num : '');
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
					sendPlayerSync();
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
			if (data.ret == 1) {
				refreshSongs(data);
				sendPlayerSync();
			}
		});
	});
}

function friendRequestListener() {
	$('.friendRequestButton').click(function() {
		var fid = $(this).attr('data-pid');
		$.post('/requests', {'id': fid}, function() {
			sendFriendRequest(fid);
		});
	});
	$('#req-agree').click(function() {
		$.get('/connect/' + $(this).attr('data-pid'), function(data) {
			if (data.ret == 1) {
				sendPlayerSync();
			}
			$.pjax({url: '/notice', container: '#main'})
		});
	});
	$('#req-decline').click(function() {
		$.ajax({
			type: 'DELETE',
			url: '/requests',
			data: {'id': $(this).attr('data-pid')}
		}).done(function(data) {
			$.pjax({url: '/notice', container: '#main'})
		});
	});
}


/* Page load listeners */

function toggleListener() {
	$('a[href="#play"]').click(function() {
		$.ajax({
			type: 'PUT',
			url: '/player',
			data: {'status': $('div.sm2-bar-ui').hasClass('playing') ? 'paused' : 'playing', 'sid': $('li.selected').children('a').first().attr('song-id')}
		}).done(function(data) {
			if (data.ret == 1) {
				sendPlayerToggle(data.player.status);
			}
		});
	});
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


/* Player related */

function refreshSongs(data) {
	var song = data['player']['song'];
	var playlist = data['player']['playlist'];
	if (playlist.length > 0) {
		var template = Handlebars.compile($("#player-playlist-template").html());
		$('#player-playlist').html(template({'playlist': playlist}));
		$('#song-img').attr('src', song['img']);
		$('div.sm2-playlist-target').html('<ul class="sm2-playlist-bd"><li>' + song['name'] + ' - ' + song['artist']['name'] + '</li></ul>');
		$('#player-playlist>li:first').addClass('selected');
		addLyric(song['id']);
		if (data.player.status == 'playing') {
			globalPlayLink($('span[song-id=' + data.player.song.id + ']').prev().get(0));
		}
	} else {
		$('#player-playlist').html('<li><a href="javascript:void(0);"></a></li>');
		$('#song-img').attr('src', $('#data-logo-img').attr('value'));
		$('div.sm2-playlist-target').html('<ul class="sm2-playlist-bd"><li></li></ul>');
		addLyric('xxx');
	}
	$('#song-num').html(playlist.length);
	clearSongListener();
	deleteSongListener();
	changeSongListener();
}

function addLyric(sid) {
	$.get('/lyrics/' + sid, function(data) {
		var template = Handlebars.compile($("#song-lyrics-template").html());
		$('#song-name').html(data['name']);
		$('#song-lyrics').html(template({'lyrics': data['lyrics']}));
	});
}

function clearSongListener() {
	$('.clear-song').click(function() {
		if ($('div.sm2-bar-ui').hasClass('playing')) {
			startStopSong();
		}
		$.ajax({
			type: "DELETE",
			url: "/player/playlist"
		}).done(function(data) {
			if (data['ret'] == 1) {
				refreshSongs(data);
				sendPlayerSync();
			}
		});
	});
}

function deleteSongListener() {
	$('.delete-song').click(function() {
		if ($('div.sm2-bar-ui').hasClass('playing')) {
			if ($('li.selected span').attr('song-id') == $(this).attr('song-id')) {
				startStopSong();
			}
		}
		$.ajax({
			type: "DELETE",
			url: "/player/playlist/" + $(this).attr('song-id')
		}).done(function(data) {
			if (data['ret'] == 1) {
				refreshSongs(data);
				sendPlayerSync();
			}
		});
	});
}

function changeSongListener() {
	$('a[song-id]').click(function() {
		skipPlayerSong($(this).attr('song-id'));
	});
}

function skipPlayerSong(sid) {
	$.ajax({
		type: 'PUT',
		url: '/player',
		data: {'status': 'playing', 'sid': sid}
	}).done(function(data) {
		if (data['ret'] == 1) {
			refreshSongs(data);
			sendPlayerSync();
		}
	});
}

function startStopSong() {
	var evt = $.Event('click');
	evt.target = $('a.sm2-inline-button').get(0);
	globalActions.play(evt);
}


/* WebSocket related */

var ws;

function connectWebSocket() {
	ws = new WebSocket('ws://' + $('#data-ws-host').attr('value') + ':' + $('#data-ws-port').attr('value'));
	ws.onopen = function () {
		ws.send(JSON.stringify({'from':$('#data-mine-id').attr('value')}));
	};
	ws.onmessage = function (e) {
		var msg = $.parseJSON(e.data);
		console.log(msg);
		if (msg.type === 'player_sync') {
			loadSongs();
		} else if (msg.type === 'player_toggle') {
			var status = $('div.sm2-bar-ui').hasClass('playing') ? 'playing' : 'paused';
			if (status != msg.status) {
				startStopSong();
			}
		} else if (msg.type === 'friend_request') {
			$.get('/requests', function(data) {
				refreshNotice();
				if ($(location).attr('pathname') == '/notice') {
					$.pjax({url: '/notice', container: '#main'})
				}
			});
		}
	};
}

function sendPlayerSync() {
	ws.send(JSON.stringify({
		'from': $('#data-mine-id').attr('value'),
		'type': 'player_sync'
	}));
}

function sendPlayerToggle(status) {
	ws.send(JSON.stringify({
		'from': $('#data-mine-id').attr('value'),
		'type': 'player_toggle',
		'status': status
	}));
}

function sendFriendRequest(to) {
	ws.send(JSON.stringify({
		'from': $('#data-mine-id').attr('value'),
		'type': 'friend_request',
		'to': to
	}));
}

