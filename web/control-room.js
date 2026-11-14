(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const params=new URL(location.href).searchParams;
  let language=params.get('lang')==='en'?'en':'vi';
  const copy={
    roomTitle:['PHÒNG ĐIỀU KHIỂN','CONTROL ROOM'],prototype:['BẢN THỬ','PROTOTYPE'],loading:['Đang mở khoang tàu…','Opening the cabin…'],
    fallbackTitle:['Chưa mở được phòng 3D','The 3D room could not open'],fallbackBody:['Bạn vẫn có thể dùng hai lối tắt bên dưới để thử tablet và hội thoại.','Use the two station shortcuts below to try the tablet and conversation.'],reload:['Tải lại','Reload'],
    move:['Di chuyển','Move'],interact:['Tương tác','Interact'],back:['Quay lại','Back'],next:['Tiếp theo','Next'],tryAgain:['Thử lại','Try again'],quizLabel:['BÀI THỬ SPHEREx','SPHEREx DEMO QUIZ'],
    explore:['Di chuyển tới tablet hoặc Alien X.','Walk to the tablet or Alien X.'],exploreShort:['Khám phá khoang tàu','Explore the cabin'],tabletNear:['A / E · Nhấc tablet lên','A / E · Pick up the tablet'],alienNear:['A / E · Nói chuyện với Alien X','A / E · Talk to Alien X'],
    walkingTablet:['Đang tới tablet…','Walking to the tablet…'],walkingAlien:['Đang tới Alien X…','Walking to Alien X…'],pickup:['Gagoo đang nhấc tablet lên.','Gagoo is picking up the tablet.'],tabletStatus:['Tablet đang trống. B / Esc để đặt xuống.','The tablet is blank. B / Esc to put it down.'],dialogueStatus:['A / E · Tiếp tục hội thoại. B / Esc · Quay lại.','A / E · Continue. B / Esc · Back.'],studyStatus:['Chọn một đáp án trên màn hình.','Choose an answer on the screen.'],
    tabletTitle:['Tablet trống','Blank tablet'],dialogueTitle:['Hội thoại với Alien X','Conversation with Alien X'],studyTitle:['Bài thử SPHEREx','SPHEREx demo quiz'],close:['Đóng','Close'],
    correct:['Đúng rồi!','Correct!'],incorrect:['Chưa đúng — cùng xem lý do.','Not quite — here is why.'],done:['Về phòng điều khiển','Back to the room'],finish:['Bạn đã hoàn thành hai câu hỏi thử.','You completed both demo questions.'],
    pause:['Dừng chuyển động trang trí','Pause decorative motion'],resume:['Tiếp tục chuyển động trang trí','Resume decorative motion'],up:['Đi lên','Move up'],down:['Đi xuống','Move down'],left:['Đi trái','Move left'],right:['Đi phải','Move right'],controls:['Điều khiển trò chơi','Game controls'],stations:['Đi tới điểm tương tác','Go to a station'],canvas:['Gagoo trong phòng điều khiển, cạnh tablet và Alien X','Gagoo in the control room, beside a tablet and Alien X'],
    dialogueOne:['Chào Gagoo! Mình là Alien X. Chào mừng tới khoang học tập của chúng ta.','Hey Gagoo! I am Alien X. Welcome to our learning cabin.'],dialogueTwo:['Muốn thử một bài nhỏ về SPHEREx không? Chọn “test” để bắt đầu.','Ready for a little SPHEREx challenge? Choose “test” to begin.']
  };
  const text=key=>copy[key]?.[language==='en'?1:0]||key;
  const questions=[
    {id:'infrared',prompt:['SPHEREx quan sát loại ánh sáng nào?','What kind of light does SPHEREx observe?'],answer:'infrared',options:[['radio','Sóng vô tuyến','Radio waves'],['infrared','Ánh sáng hồng ngoại','Infrared light'],['visible','Chỉ ánh sáng nhìn thấy','Only visible light'],['xray','Tia X','X-rays']],explanation:['SPHEREx khảo sát bầu trời bằng ánh sáng hồng ngoại gần. Mắt người không nhìn thấy phần lớn dải này; các màu trong ảnh trình bày được gán để giúp ta đọc dữ liệu.','SPHEREx surveys the sky in near-infrared light. Most of this range is invisible to human eyes; colors in displayed images are assigned to help us read the data.'],source:'https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/'},
    {id:'channels',prompt:['“102 màu” của SPHEREx nói tới điều gì?','What do SPHEREx’s “102 colors” mean?'],answer:'channels',options:[['cameras','102 camera riêng biệt','102 separate cameras'],['planets','102 hành tinh được chụp','102 photographed planets'],['channels','102 kênh bước sóng','102 wavelength channels'],['satellites','102 vệ tinh nhỏ','102 tiny satellites']],explanation:['Đó là 102 kênh phổ trong dải hồng ngoại. SPHEREx dùng sáu detector cùng các bộ lọc thay đổi theo vị trí để thu các phép đo tạo thành phổ — không phải 102 camera.','They are 102 spectral channels in the infrared. SPHEREx uses six detectors and filters that vary with position to collect measurements that build a spectrum — not 102 cameras.'],source:'https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/'}
  ];
  const reduced=matchMedia('(prefers-reduced-motion: reduce)');
  let state='room',scene,sceneReady=false,frame=0,last=0,paused=false,near='',dialogueIndex=0,questionIndex=0,answer=null,returnFocus=null,walking='',disposed=false;
  const keys=new Set(),heldDirections=new Map();
  function say(key){$('room-status').textContent=text(key);}
  function setState(next){state=next;document.body.dataset.gameState=next;keys.clear();clearDirections();$('room-overlay').hidden=!['tablet','dialogue','study'].includes(state);
    for(const panel of ['tablet','dialogue','study'])$(`room-${panel}-panel`).hidden=panel!==state;
    $('room-tablet-shortcut').disabled=$('room-alien-shortcut').disabled=state!=='room';
    document.querySelectorAll('[data-direction]').forEach(button=>button.disabled=state!=='room');
    $('room-close').hidden=!['tablet','dialogue','study'].includes(state);
    if(state==='tablet'){$('room-overlay-title').textContent=text('tabletTitle');say('tabletStatus');}
    if(state==='dialogue'){$('room-overlay-title').textContent=text('dialogueTitle');say('dialogueStatus');}
    if(state==='study'){$('room-overlay-title').textContent=text('studyTitle');say('studyStatus');}
    updateAction();
  }
  function updateAction(){
    $('room-action-label').textContent=text(state==='dialogue'?'next':'interact');
    $('room-interact').setAttribute('aria-label',text(state==='dialogue'?'next':'interact'));
    $('room-back').setAttribute('aria-label',text('back'));
    $('room-prompt-text').textContent=near==='tablet'?text('tabletNear').split(' · ')[1]:near==='alien'?text('alienNear').split(' · ')[1]:text('exploreShort');
    $('room-prompt').dataset.active=String(Boolean(near));
  }
  function updateLanguage(){
    document.documentElement.lang=language;
    document.querySelectorAll('[data-text]').forEach(node=>node.textContent=text(node.dataset.text));
    $('room-language').textContent=language==='vi'?'EN':'VI';$('room-language').setAttribute('aria-label',language==='vi'?'Switch to English':'Chuyển sang tiếng Việt');
    $('room-close').setAttribute('aria-label',text('close'));$('room-motion').setAttribute('aria-label',text(paused?'resume':'pause'));
    $('room-screen').setAttribute('aria-label',text('roomTitle'));$('room-canvas').setAttribute('aria-label',text('canvas'));$('room-controls').setAttribute('aria-label',text('controls'));document.querySelector('.room-stations').setAttribute('aria-label',text('stations'));
    document.querySelectorAll('[data-direction]').forEach(button=>button.setAttribute('aria-label',text(button.dataset.direction)));
    $('room-tablet-panel').setAttribute('aria-label',text('tabletTitle'));document.querySelector('.room-tablet-display').setAttribute('aria-label',text('tabletTitle'));
    document.title=`${language==='en'?'Control room':'Phòng điều khiển'} · sphere x learn`;
    if(state==='room')say(walking?walking==='tablet'?'walkingTablet':'walkingAlien':near==='tablet'?'tabletNear':near==='alien'?'alienNear':'explore');
    else if(state==='pickup')say('pickup');else if(state==='tablet')say('tabletStatus');else if(state==='dialogue'){say('dialogueStatus');renderDialogue();}else if(state==='study'){say('studyStatus');renderQuestion();}
    updateAction();
  }
  function renderDialogue(){ $('room-dialogue-text').textContent=text(dialogueIndex===0?'dialogueOne':'dialogueTwo');$('room-dialogue-next').hidden=dialogueIndex!==0;$('room-test-choice').hidden=dialogueIndex!==1; }
  function openAlien(){returnFocus=document.activeElement;walking='';scene?.cancelGoal();dialogueIndex=0;setState('dialogue');renderDialogue();$('room-dialogue-next').focus({preventScroll:true});}
  function openTablet(){returnFocus=document.activeElement;walking='';setState('pickup');say('pickup');if(sceneReady){scene.beginPickup();}else{setState('tablet');$('room-close').focus({preventScroll:true});}}
  function arrived(which){walking='';if(state!=='room')return;if(which==='tablet')openTablet();if(which==='alien')openAlien();}
  function goTo(which){if(state!=='room')return;if(!sceneReady){arrived(which);return;}walking=which;say(which==='tablet'?'walkingTablet':'walkingAlien');if(scene.goTo(which)===false){walking='';say('explore');}}
  function closeOverlay(){if(state==='room'){scene?.cancelGoal();walking='';say('explore');return;}if(state==='tablet'||state==='pickup')scene?.putDown();setState('room');say(near==='tablet'?'tabletNear':near==='alien'?'alienNear':'explore');const focus=returnFocus?.isConnected?returnFocus:$('room-interact');focus.focus({preventScroll:true});returnFocus=null;}
  function nextDialogue(){if(state!=='dialogue')return;if(dialogueIndex===0){dialogueIndex=1;renderDialogue();$('room-test-choice').focus({preventScroll:true});}else openQuiz();}
  function openQuiz(){questionIndex=0;answer=null;setState('study');renderQuestion();$('room-study-panel').scrollTop=0;$('room-quiz-options').querySelector('button')?.focus({preventScroll:true});}
  function renderQuestion(){
    const question=questions[questionIndex],lang=language==='en'?1:0;$('room-quiz-title').textContent=question.prompt[lang];$('room-quiz-count').textContent=`0${questionIndex+1} / 0${questions.length}`;
    const options=$('room-quiz-options');options.replaceChildren();
    question.options.forEach((option,index)=>{const button=document.createElement('button');button.type='button';button.dataset.answer=option[0];const label=document.createElement('b');label.textContent=String.fromCharCode(65+index);const span=document.createElement('span');span.textContent=option[lang+1];button.append(label,span);button.addEventListener('click',()=>chooseAnswer(option[0]));options.append(button);});
    renderFeedback();
  }
  function renderFeedback(){
    const question=questions[questionIndex],correct=answer===question.answer,answered=answer!==null;
    $('room-quiz-feedback').hidden=!answered;$('room-quiz-next').hidden=!answered||!correct;$('room-quiz-retry').hidden=!answered||correct;
    for(const button of $('room-quiz-options').querySelectorAll('button')){button.disabled=answered;delete button.dataset.result;if(answered&&button.dataset.answer===answer)button.dataset.result=correct?'correct':'incorrect';}
    if(!answered)return;
    $('room-quiz-feedback').dataset.correct=String(correct);$('room-quiz-result').textContent=text(correct?'correct':'incorrect');$('room-quiz-explanation').textContent=question.explanation[language==='en'?1:0];$('room-quiz-source').href=question.source;
    $('room-quiz-next').textContent=text(questionIndex===questions.length-1?'done':'next');
  }
  function revealFeedback(){
    const panel=$('room-study-panel'),feedback=$('room-quiz-feedback');
    // Scroll only the quiz panel: the game and physical controls keep their positions.
    const target=panel.scrollTop+feedback.getBoundingClientRect().top-panel.getBoundingClientRect().top-12;
    panel.scrollTo({top:Math.max(0,target),behavior:'instant'});
  }
  function chooseAnswer(value){if(state!=='study'||answer!==null)return;answer=value;renderFeedback();const correct=value===questions[questionIndex].answer;(correct?$('room-quiz-next'):$('room-quiz-retry')).focus({preventScroll:true});revealFeedback();}
  function nextQuestion(){if(state!=='study'||answer!==questions[questionIndex].answer)return;if(questionIndex===questions.length-1){closeOverlay();say('finish');return;}questionIndex++;answer=null;renderQuestion();$('room-study-panel').scrollTop=0;$('room-quiz-options').querySelector('button').focus({preventScroll:true});}
  function retryQuestion(){if(state!=='study')return;answer=null;renderFeedback();$('room-study-panel').scrollTop=0;$('room-quiz-options').querySelector('button').focus({preventScroll:true});}
  function interact(){if(state==='dialogue'){nextDialogue();return;}if(state==='study'){if(answer!==null){answer===questions[questionIndex].answer?nextQuestion():retryQuestion();}else $('room-quiz-options').querySelector('button')?.focus({preventScroll:true});return;}if(state!=='room')return;if(near==='tablet')openTablet();else if(near==='alien')openAlien();else say('explore');}
  function clearDirections(){heldDirections.clear();document.querySelectorAll('[data-held]').forEach(button=>button.removeAttribute('data-held'));}
  const directionForKey={ArrowUp:'up',w:'up',W:'up',ArrowDown:'down',s:'down',S:'down',ArrowLeft:'left',a:'left',A:'left',ArrowRight:'right',d:'right',D:'right'};
  document.addEventListener('keydown',event=>{
    if(event.altKey||event.ctrlKey||event.metaKey)return;
    if(event.key==='Escape'){event.preventDefault();closeOverlay();return;}
    if(event.target.matches('input,textarea,select'))return;
    if(directionForKey[event.key]){if(state==='room'){event.preventDefault();keys.add(directionForKey[event.key]);walking='';}return;}
    if((event.key==='e'||event.key==='E')&&!event.repeat){event.preventDefault();interact();}
  });
  document.addEventListener('keyup',event=>{if(directionForKey[event.key])keys.delete(directionForKey[event.key]);});
  for(const button of document.querySelectorAll('[data-direction]')){
    button.addEventListener('pointerdown',event=>{if(state!=='room'||event.button!==0)return;event.preventDefault();button.setPointerCapture(event.pointerId);heldDirections.set(event.pointerId,button.dataset.direction);button.dataset.held='true';walking='';});
    const release=event=>{heldDirections.delete(event.pointerId);button.removeAttribute('data-held');};
    button.addEventListener('pointerup',release);button.addEventListener('pointercancel',release);button.addEventListener('lostpointercapture',release);
    button.addEventListener('click',event=>{if(event.detail===0&&state==='room'){keys.add(button.dataset.direction);setTimeout(()=>keys.delete(button.dataset.direction),150);}});
  }
  $('room-tablet-shortcut').addEventListener('click',()=>goTo('tablet'));$('room-alien-shortcut').addEventListener('click',()=>goTo('alien'));
  $('room-interact').addEventListener('click',interact);$('room-back').addEventListener('click',closeOverlay);$('room-close').addEventListener('click',closeOverlay);$('room-dialogue-next').addEventListener('click',nextDialogue);$('room-test-choice').addEventListener('click',openQuiz);$('room-quiz-next').addEventListener('click',nextQuestion);$('room-quiz-retry').addEventListener('click',retryQuestion);$('room-reload').addEventListener('click',()=>location.reload());
  $('room-language').addEventListener('click',()=>{language=language==='vi'?'en':'vi';const url=new URL(location.href);url.searchParams.set('lang',language);history.replaceState(history.state,'',url);updateLanguage();});
  $('room-motion').addEventListener('click',()=>{paused=!paused;scene?.setPaused(paused);$('room-motion').setAttribute('aria-pressed',String(paused));$('room-motion').textContent=paused?'▷':'Ⅱ';$('room-motion').setAttribute('aria-label',text(paused?'resume':'pause'));});
  $('room-canvas').addEventListener('click',event=>{if(state!=='room'||!sceneReady)return;const which=scene.pick(event.clientX,event.clientY);if(which)goTo(which);});
  function input(){const all=new Set([...keys,...heldDirections.values()]);return{x:Number(all.has('right'))-Number(all.has('left')),y:Number(all.has('down'))-Number(all.has('up'))};}
  function tick(now){frame=0;if(disposed||document.hidden||!sceneReady)return;const dt=last?Math.min(.04,(now-last)/1000):1/60;last=now;scene.update(dt,input(),state==='room');scene.render();frame=requestAnimationFrame(tick);}
  function resume(){if(sceneReady&&!frame&&!document.hidden&&!disposed){last=0;frame=requestAnimationFrame(tick);}}
  function stop(){keys.clear();clearDirections();if(frame)cancelAnimationFrame(frame);frame=0;last=0;}
  function fail(){sceneReady=false;stop();document.body.dataset.sceneState='error';$('room-loading').hidden=true;$('room-error').hidden=false;near='';updateAction();if(state==='pickup'){setState('tablet');$('room-close').focus({preventScroll:true});}}
  addEventListener('blur',()=>{keys.clear();clearDirections();});
  document.addEventListener('visibilitychange',()=>document.hidden?stop():resume());
  addEventListener('pagehide',event=>{stop();if(!event.persisted){disposed=true;scene?.dispose();}});
  addEventListener('pageshow',event=>{if(event.persisted)resume();});
  addEventListener('resize',()=>{scene?.resize();scene?.render();});
  updateLanguage();
  import('./control-room-scene.js?v=1').then(({createControlRoom})=>{
    if(disposed)return;
    scene=createControlRoom({canvas:$('room-canvas'),reduced,onNear(value){near=value;if(state==='room'&&!walking)say(near==='tablet'?'tabletNear':near==='alien'?'alienNear':'explore');updateAction();},onArrive:arrived,onPickup(){if(state==='pickup'){setState('tablet');$('room-close').focus({preventScroll:true});}},onError:fail});
    sceneReady=true;document.body.dataset.sceneState='ready';$('room-loading').hidden=true;resume();
  }).catch(fail);
})();
