// -*- javascript -*-
/*
function parseCSV() {
    var info = el('userValue').value;
    var temp = [];
    temp = info.split(',');
    alert(info.join('\t'));
}
*/

function ruptime()
{
    //var filePath = "http://127.0.0.1:6502/ruptime";
    var filePath = "/ruptime";
    try{
	xmlhttp = new XMLHttpRequest();
	xmlhttp.open("GET",filePath,false);
	xmlhttp.send(null);
	var fileContent = xmlhttp.responseText;
	var fileArray = fileContent.split('\n')
	var lines = new Array();
	for(var i=0; i<fileArray.length-1; i++){
	    lines.push(fileArray[i].split("\t"));
	}
	return lines;
    }
    catch(e){
	return [];
    }
}




function recurse(fileArray,depth)
{
    var subdir = new Array();
    while( fileArray[0] != "" ){
	var columns = fileArray.shift().split("\t");
	columns[2] = recurse(fileArray,depth+1);
	subdir.push(columns);
    }
    fileArray.shift();
    return subdir;
}



function df()
{
    var filePath = "/df";
    xmlhttp = new XMLHttpRequest();
    xmlhttp.open("GET",filePath,false);
    xmlhttp.send(null);
    var fileContent = xmlhttp.responseText;
    var fileArray = fileContent.split('\n')
    var lines = new Array();
    for(var i=0; i<fileArray.length-1; i++){
	lines.push(fileArray[i].split("\t"));
    }
    return lines;
}


var winx = screen.width;
var winy = screen.height;
var winx = 640;
var winy = 960;
var zoom = 6.0;
var unit = 0.5;
var labelw = 0.2;
var count = 1000;
var delay = 0;
void setup()
{
    size(winx,winy);
    smooth();
    
    // limit the number of frames per second
    frameRate(1);
    colorMode(HSB,100);
    // set the width of the line. 
    //strokeWeight(12);
    strokeCap(SQUARE);
}


void draw()
{
    if ( count++ > 3 ){ //update every 3 seconds
	//println(lines[0]);
	float x = 0;
	float y = 0;
	background(0,0,10);

	//df
	var lines = df();
	for(int i=0; i<lines.length; i++){
	    float size = lines[i][2];
	    float used = (float)lines[i][1] / size;
	    size /= 4000000000;
	    fill((1.0-used)*80,100,100);
	    float barheight = (int)(size*zoom);
	    rect(winx*labelw,y,used*winx*(1-labelw),barheight);
	    fill(0,0,100);
	    textAlign(RIGHT); 
	    textSize(zoom*3); 
	    text(lines[i][0],winx*labelw,y+barheight/2+zoom);
	    y += barheight+1;
	    //println({lines[i][0],cores,y,});
	}


	count = 0;
	var lines = ruptime();
	if ( lines.length == 0 ){
	    delay ++;
	    fill(100,0,100);
	    noStroke();
	    for(int i=0;i<delay;i++){
		rect(i*winx/200,0,winx/250,winy/100);
	    }
	    return;
	}
	delay = 0;

	float extra = 1.0 - labelw - unit;
	noStroke();
	fill(0,0,20);
	rect(winx*(unit+labelw),y,winx*extra/4,winy);
	fill(0,0,30);
	rect(winx*(unit+labelw+extra*1./4),y,winx*extra/4,winy);
	fill(0,0,40);
	rect(winx*(unit+labelw+extra*2./4),y,winx*extra/4,winy);
	fill(0,0,50);
	rect(winx*(unit+labelw+extra*3./4),y,winx*extra/4,winy);
	for(int i=0; i<lines.length; i++){
	    float cores = lines[i][2];
	    float loadw = lines[i][3] / cores;
	    float load = loadw;
	    float load0 = loadw;
	    if(load > 1.0){
		load = 1.0;
	    }
	    if (loadw < 1.0){
		loadw = 1.0;
	    }
	    noStroke();
	    float bar = load*unit;
	    if (loadw > 1 ){
		//w approaches slowly to 0 for larger load
		var w = exp(-(loadw-1));
		fill(0,w*100,100);
		bar = unit+(loadw-1)*extra/4;
	    }
	    else{
		fill((1.0-load)*80,100,100); 
	    }
	    float barheight = (int)(sqrt(cores)*zoom);
	    rect(winx*labelw,y,winx*bar,barheight);
	    fill(0,0,100);
	    textAlign(RIGHT); 
	    textSize(zoom*3); 
	    text(lines[i][0],winx*labelw,y+barheight/2+zoom);
	    y += barheight+1;
	    //println({lines[i][0],cores,y,});
	}
	var x = winx - zoom;
	var y = zoom*10;
	var date = new Date();

	var min = date.getMinutes();
	var now;
	if ( min < 10 ){
	    now = date.getHours() + ":0" + date.getMinutes();
	}
	else{
	    now = date.getHours() + ":" + date.getMinutes();
	}
	textSize(zoom*10);
	textAlign(RIGHT);
	fill(0,0,50);
	text(now,x,y);
    }
}

