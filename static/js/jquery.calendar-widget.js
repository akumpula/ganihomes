(function($) {

	function calendarWidget(el, params) {

		var now   = new Date();
		var thismonth = now.getMonth();
		var thisyear  = now.getYear() + 1900;

		var opts = {
			month: thismonth,
			year: thisyear,
			firstWeekDay: 0,
            monthNames : ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
            dayNames : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
		};

		$.extend(opts, params);

//		var monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
//		var dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        var monthNames = opts.monthNames
        var dayNames = opts.dayNames
        var firstWeekDay = opts.firstWeekDay
		month = i = parseInt(opts.month);
		year = parseInt(opts.year);
		var m = 0;
		var table = '';

			// next month
			if (month == 11) {
				var next_month = '<a href="?month=' + 1 + '&amp;year=' + (year + 1) + '" title="' + monthNames[0] + ' ' + (year + 1) + '">' + monthNames[0] + ' ' + (year + 1) + '</a>';
			} else {
				var next_month = '<a href="?month=' + (month + 2) + '&amp;year=' + (year) + '" title="' + monthNames[month + 1] + ' ' + (year) + '">' + monthNames[month + 1] + ' ' + (year) + '</a>';
			}

			// previous month
			if (month == 0) {
				var prev_month = '<a href="?month=' + 12 + '&amp;year=' + (year - 1) + '" title="' + monthNames[11] + ' ' + (year - 1) + '">' + monthNames[11] + ' ' + (year - 1) + '</a>';
			} else {
				var prev_month = '<a href="?month=' + (month) + '&amp;year=' + (year) + '" title="' + monthNames[month - 1] + ' ' + (year) + '">' + monthNames[month - 1] + ' ' + (year) + '</a>';
			}

			table += ('<h3 id="current-month">'+monthNames[month]+' '+year+'</h3>');
			// uncomment the following lines if you'd like to display calendar month based on 'month' and 'view' paramaters from the URL
			//table += ('<div class="nav-prev">'+ prev_month +'</div>');
			//table += ('<div class="nav-next">'+ next_month +'</div>');
			table += ('<table class="calendar-month " ' +'id="calendar-month'+i+' " cellspacing="0">');

			table += '<tr>';
//        console.log(firstWeekDay)
			for (d=0; d<7; d++) {
                var dy = d+firstWeekDay <7 ? d+firstWeekDay : d+firstWeekDay - 7

//                    console.log(dy)
				table += '<th class="weekday">' + dayNames[dy] + '</th>';
			}

			table += '</tr>';

			var days = getDaysInMonth(month,year);
            var firstDayDate=new Date(year,month,1);
            var firstDay=firstDayDate.getDay();

			var prev_days = getDaysInMonth(month,year);
            var firstDayDate=new Date(year,month,1);
            var firstDay=firstDayDate.getDay();

			var prev_m = month == 0 ? 11 : month-1;
			var prev_y = prev_m == 11 ? year - 1 : year;
			var prev_days = getDaysInMonth(prev_m, prev_y);

//            firstDay = firstDay+firstWeekDay >7 ? firstDay+firstWeekDay : firstDay+firstWeekDay - 7
			firstDay = (firstDay == 0 && firstDayDate) ? 7 : firstDay;
            firstDay = firstDay-firstWeekDay >0 ? firstDay-firstWeekDay : firstDay-firstWeekDay + 7
//            console.log(firstDay)
			var i = 0;
            for (j=0;j<42;j++){

              if ((j<firstDay)){
                table += ('<td class="other-month"><span class="day">'+ (prev_days-firstDay+j+1) +'</span></td>');
			  } else if ((j>=firstDay+getDaysInMonth(month,year))) {
				i = i+1;
                table += ('<td class="other-month"><span class="day">'+ i +'</span></td>');
              }else{
                dy = (j-firstDay+1)
                dy = dy<10 ? '0'+dy : dy
                mn = month + 1
                mn = mn<10 ? '0'+mn : mn

                table += ('<td class="current-month day'+dy+'" id="i'+year+''+mn+''+dy+'"><span class="day">'+dy+'</span></td>');
              }
              if (j%7==6)  table += ('</tr>');
            }

            table += ('</table>');

		el.append('<div class="caltblwrp">'+table + '</div>');
	}

	function getDaysInMonth(month,year)  {
		var daysInMonth=[31,28,31,30,31,30,31,31,30,31,30,31];
		if ((month==1)&&(year%4==0)&&((year%100!=0)||(year%400==0))){
		  return 29;
		}else{
		  return daysInMonth[month];
		}
	}


	// jQuery plugin initialisation
	$.fn.calendarWidget = function(params) {

		calendarWidget(this, params);

		return this;
	};

})(jQuery);
