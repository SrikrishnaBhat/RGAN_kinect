
% Demo 1: Visualize a sequence.
%
% Author: Sebastian Nowozin <Sebastian.Nowozin@microsoft.com>

disp(['Visualizing sequence parsed_G3']);

% [X,Y,tagset]=load_file('P3_1_1_p23');
% X = load('../data/parsed_created_G3.csv');
% X = load('../data/merged2.csv');
X = load('../data/parsed_synthetic_dance_merged_100.csv');
T=size(X,1);	% Length of sequence in frames
X = X / 1000;
% Animate sequence
h=axes;
for ti=1:T
	skel_vis(X,ti,h);
	drawnow;
	pause(1/30);
	cla;
end