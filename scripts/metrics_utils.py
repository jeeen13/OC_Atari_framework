import numpy as np
from termcolor import colored
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import euclidean, cdist


np.set_printoptions(precision=1)
USE_IPDB = False
MIN_DIST_DETECTION = 5


def format_values(dictionary):
    keys, values = dictionary.keys(), dictionary.values()
    return {key: round(val, 1) for key, val in zip(keys, (np.array(list(values)) * 100))}


class DetectionScores():
    def __init__(self) -> None:
        self.true_pos = {}
        self.false_pos = {}
        self.false_neg = {}
        self.iou = None

    def update(self, det_dict):
        for cat, (TP, FP, FN) in det_dict.items():
            if not cat in self.true_pos:
                self.true_pos[cat] = TP
                self.false_pos[cat] = FP
                self.false_neg[cat] = FN
            else:
                self.true_pos[cat] += TP
                self.false_pos[cat] += FP
                self.false_neg[cat] += FN
    
    @property
    def cat_precisions(self):
        try:
            return {cat: self.true_pos[cat]/(self.true_pos[cat]+self.false_pos[cat]) for cat in self.true_pos if self.true_pos[cat]+self.false_pos[cat]}
        except ZeroDivisionError:
            import ipdb; ipdb.set_trace()

    @property
    def cat_recalls(self):
        try:
            return {cat: self.true_pos[cat]/(self.true_pos[cat]+self.false_neg[cat]) for cat in self.true_pos if self.true_pos[cat]+self.false_neg[cat]}
        except ZeroDivisionError:
            import ipdb; ipdb.set_trace()
    
    @property
    def cat_f_scores(self):
        prec, rec = self.cat_precisions, self.cat_recalls
        f_scores = {}
        for cat in prec.keys():
            if prec[cat] == 0 and rec[cat] == 0:
                f_scores[cat] = 0
            else:
                f_scores[cat] = 2 * prec[cat] * rec[cat] / (prec[cat] + rec[cat])
        return f_scores

    @property
    def mean_precision(self):
        return sum(self.true_pos.values())/(sum(self.true_pos.values()) + sum(self.false_pos.values()))
    
    @property
    def mean_recall(self):
        return sum(self.true_pos.values())/(sum(self.true_pos.values()) + sum(self.false_neg.values()))
    
    @property
    def mean_f_score(self):
        prec, rec = self.mean_precision, self.mean_recall
        return 2 * prec * rec / (prec + rec)

    @property
    def mean_recall(self):
        return sum(self.true_pos.values())/(sum(self.true_pos.values()) + sum(self.false_neg.values()))

    def __repr__(self) -> str:
        return "Detection stats with Cat. F-scores: \n" + str(self.cat_f_scores)
    
    @property
    def dict_summary(self):
        return {"precision": self.mean_precision, "recall": self.mean_recall, "f-score": self.mean_f_score,
                "iou": self.iou}
    

def print_all_stats(all_stats):
    linelength = 39
    print("Mean IOUs: ", round(all_stats['mean_ious'], 2))
    print("-"*linelength)
    print("\nPer class IOU: ")
    for objname, res in all_stats['per_class_ious'].items():
        if res < 0.6:
            print(colored(f"\t| {objname}: {res:.2f}", 'red'))
        elif res < 0.9:
            print(colored(f"\t| {objname}: {res:.2f}", 'yellow'))
        else:
            print(colored(f"\t| {objname}: {res:.2f}", 'green'))
    if all_stats['only_in_ram']:
        print("-"*linelength)
        print("Objects found only in ram version: ")
        for objname, res in all_stats['only_in_ram'].items():
            if eval(res) < 0.6:
                print(colored(f"\t| {objname}: {res}", 'red'))
            elif eval(res) < 0.9:
                print(colored(f"\t| {objname}: {res}", 'yellow'))
            else:
                print(colored(f"\t| {objname}: {res}", 'green'))
    if all_stats['only_in_vision']:
        print("-"*linelength)
        print("Objects found only in vision version: ")
        for objname, res in all_stats['only_in_vision'].items():
            if eval(res) < 0.6:
                print(colored(f"\t| {objname}: {res}", 'red'))
            elif eval(res) < 0.9:
                print(colored(f"\t| {objname}: {res}", 'yellow'))
            else:
                print(colored(f"\t| {objname}: {res}", 'green'))
    print("-"*linelength)


def get_iou(obj1, obj2):
    # determine the (x, y)-coordinates of the intersection rectangle
    xA = max(obj1.x, obj2.x)
    yA = max(obj1.y, obj2.y)
    xB = min(obj1.x+obj1.w, obj2.x+obj2.w)
    yB = min(obj1.y+obj1.h, obj2.y+obj2.h)
    # compute the area of intersection rectangle
    interArea = max(0, xB - xA) * max(0, yB - yA)
    # compute the area of both the prediction and ground-truth
    # rectangles
    boxAArea = (obj1.w) * (obj1.h)
    boxBArea = (obj2.w) * (obj2.h)
    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    iou = interArea / float(boxAArea + boxBArea - interArea)
    # return the intersection over union value
    return iou


def make_class_lists(ram_list, vision_list):
    """
    Creates a dictionary of object category liked with both the ram objs of this 
    category and then the vision objs of this category.
    """
    categories = set([obj.category for obj in ram_list+vision_list])
    cat_lists = {}
    for cat in categories:
        cat_lists[cat] = ([obj.center for obj in ram_list if obj.category == cat],
                             [obj.center for obj in vision_list if obj.category == cat])
    return cat_lists

def detection_stats(ram_list, vision_list):
    """
    returns the precision, recall and f1_score
    """
    cat_lists = make_class_lists(ram_list, vision_list)
    dets = {}
    for cat, (rlist, vlist) in cat_lists.items():
        TrueP = 0
        FalseP = max(0, len(rlist) - len(vlist))
        FalseN = max(0, len(vlist) - len(rlist))
        if len(rlist) > 1 and len(vlist) > 1:
            cost_m = cdist(rlist, vlist)
            row_ind, col_ind = linear_sum_assignment(cost_m)
            # reassign
            rlist = [rlist[i] for i in row_ind]
            vlist = [vlist[i] for i in col_ind]
        for ro, vo in zip(rlist, vlist):
            if euclidean(ro, vo) < MIN_DIST_DETECTION:
                TrueP += 1
            else:
                FalseN += 1
                FalseP += 1
        dets[cat] = (TrueP, FalseP, FalseN)
    return dets


def difference_objects(ram_list, vision_list):
    only_in_ram = []
    only_in_vision = []
    per_class_ious = {}
    ious = []
    dets = detection_stats(ram_list, vision_list)
    if abs(len(vision_list) - len(ram_list)) > 10 and USE_IPDB:
        import ipdb; ipdb.set_trace()
    for vobj in vision_list:
        vobj._is_in_ram = False
    for robj in ram_list:
        robj._is_in_image = False
        for vobj in vision_list:
            if robj.__class__.__name__ == vobj.__class__.__name__:
                objname = robj.__class__.__name__
                iou = get_iou(robj, vobj)
                if iou > 0:
                    ious.append(iou)
                    if objname not in per_class_ious:
                        per_class_ious[objname] = [iou]
                    else:
                        per_class_ious[objname].append(iou)
                    vobj._is_in_ram = True
                    robj._is_in_image = True
                    break
    for name, li in per_class_ious.items():
        per_class_ious[name] = np.mean(li)
    for robj in ram_list:
        if not robj._is_in_image:
            only_in_ram.append(str(robj))
    for vobj in vision_list:
        if not vobj._is_in_ram:
            only_in_vision.append(str(vobj))
    return {"mean_iou": np.mean(ious), "per_class_ious": per_class_ious,
            "only_in_ram": only_in_ram, "only_in_vision": only_in_vision,
            "objs_in_ram": [str(o) for o in ram_list],
            "objs_in_vision": [str(o) for o in vision_list], 
            "dets": dets}
