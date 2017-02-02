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

var winx = screen.width;
var winy = screen.height;
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


void banner()
{
    fill(0,0,0,20);
    noStroke();
    rect(0,0,winx,winy);
    noFill();
    stroke(100,0,100);
    strokeWeight(zoom/5);
    r = winy*0.1
    ellipse(winx/2,winy/2,r*2,r*2); 
    line(winx/2-r/1.4,winy/2+r/1.4,winx/2+r/1.4,winy/2-r/1.4); 
    textSize(zoom);
    noStroke();
    fill(0,0,100);
    textAlign(CENTER);
    text("Disconnected. Waiting for response...", winx/2, winy/2+r*2);
}


void draw()
{
    if ( count++ > 5 ){ //update every 3 seconds
        if ( screen.width < screen.height ){
            translate(screen.width,0);
            rotate(PI/2);
            winx = screen.height;
            winy = screen.width;
        }
var zoom = winx / 28.0;
	count = 0;
	var lines = ruptime();
	if ( lines.length == 0 ){
	    delay ++;
	    fill(100,0,100);
	    noStroke();
	    for(int i=0;i<delay;i++){
		rect(i*winx/200,0,winx/250,winy/100);
	    }
	    //banner();
	    return;
	}
	delay = 0;
	//println(lines[0]);
	x = 0;
	y = 0; //-sqrt(12) * zoom/4; 

	lastos = "";
        newline = 0;
        lineheight = 0;
	background(0,0,10);
        //show screen size
        fill(0,0,100);
        textAlign(RIGHT);
        var s = winx.toString()+"x"+winy.toString();
        textSize(zoom/2);
        text(s,winx,winy-zoom/2);
	for(int i=0; i<lines.length; i++){
	    if ( lastos != lines[i][1] ){
		maxcores = (lastos == "") ? 64 : 24;
		lastos = lines[i][1];
		//maxcores = (lastos == "centos") ? 64 : 12;
		lineheight = maxcores * zoom/20; 
                newline = 1;
		textSize(zoom);
		textAlign(RIGHT);
		fill(0,0,50);
		text(lastos,winx-zoom/4,y+lineheight/2);
	    }
            if ( newline ){
                y += lineheight;
                newline = 0;
                x = 0;
            }
	    float cores = lines[i][2];
	    float loadw = lines[i][3] / cores;
	    float rel   = lines[i][4];
	    load = loadw;
	    load0 = loadw;
	    if(load > 1.0){
		load = 1.0;
	    }
	    if (loadw < 1.0){
		loadw = 1.0;
	    }
	    noFill(); 
	    //strokeWeight(zoom*loadw/7);
	    var sw = zoom/12;
	    if ( maxcores < cores ){
		maxcores = cores;
	    }
	    //outermost radius
	    r = cores * rel * zoom/22;
	    x += r + zoom/8; 
	    r0 = r;
            var outermost = 1;
	    while ( load0 >= 0.0 ){
                //black ring
                if ( outermost ){
		    strokeWeight(sw+sw*0.5);
		    stroke(0,0,0);
		    ellipse(x,y-lineheight/2,r0*2-sw*0.5,r0*2-sw*0.5);
                    outermost = 0;
                }
		strokeWeight(sw);
		//if (load < 0.333){
		//   stroke(66, 50, load*300);
		//}
		//else if (loadw > 1 ){
		if (loadw > 1 ){
		    //w approaches slowly to 0 for larger load
		    var w = exp(-(loadw-1));
		    stroke(0,w*100,100);
		}
		else{
		    stroke((1.0-load)*100,load*100,100); 
		}
		arc(x,y-lineheight/2,r0*2,r0*2,-PI*0.5,PI*(-0.5+2*load0));
		load0 -= 1.0;
		sw *= (r0-sw)/r0;
		r0 -= sw*1.6;
	    }
	    fill(0,0,100);
	    //noStroke();
	    textAlign(CENTER); 
	    textSize(r/1.7); 
	    pushMatrix();
	    translate(x,y-lineheight/2);
	    rotate(-PI/4);
	    text(lines[i][0],0,0);
	    popMatrix();
	    x += r * 0.5;
	    if ( x > winx*0.95 ){
                newline = 1;
		lineheight = sqrt(12) * zoom/2; 

	    }
	}
	var x = winx - zoom/8;
	var y = zoom;
	var date = new Date();

	var min = date.getMinutes();
	var now;
	if ( min < 10 ){
	    now = date.getHours() + ":0" + date.getMinutes();
	}
	else{
	    now = date.getHours() + ":" + date.getMinutes();
	}
	textSize(zoom);
	textAlign(RIGHT);
	fill(0,0,50);
	text(now,x,y);
    }
}

